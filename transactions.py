# 3. services/transactions.py (Cerebro financiero final)

import logging
from uuid import UUID
from decimal import Decimal, ROUND_HALF_UP
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.domain import (
    Jugador,
    Temporada,
    EstadoJugador,
    EventoFeed,
    TransaccionFinanciera
)

logger = logging.getLogger(__name__)


async def confirmar_transaccion(
    tx_id: UUID,
    db: AsyncSession
) -> dict:
    """
    Ejecuta la confirmación financiera de una transacción.

    Reglas:
    - Dinero se acumula únicamente en temporada.fondo_global
    - No hay distribución entre jugadores
    - Calorías compradas se inyectan al comprador
    - Desbloqueo solo ocurre si era pago_deuda
    - No se emiten WebSockets aquí (solo se retornan eventos)
    - No se hace commit aquí (lo hace el router)
    """

    eventos_ws = []

    # -----------------------------------------------------
    # 1️. Lock de la Transacción (Previene doble confirmación)
    # -----------------------------------------------------
    result_tx = await db.execute(
        select(TransaccionFinanciera)
        .where(TransaccionFinanciera.id == tx_id)
        .with_for_update()
    )
    tx = result_tx.scalars().first()

    if not tx:
        raise HTTPException(status_code=404, detail="Transacción no encontrada.")

    if tx.estado_pago == "confirmado":
        raise HTTPException(status_code=400, detail="La transacción ya fue confirmada.")

    # -----------------------------------------------------
    # 2️. Lock de Temporada Activa
    # -----------------------------------------------------
    result_temp = await db.execute(
        select(Temporada)
        .where(Temporada.estado == "activa")
        .with_for_update()
    )
    temporada = result_temp.scalars().first()

    if not temporada:
        raise HTTPException(status_code=400, detail="No hay temporada activa.")

    # -----------------------------------------------------
    # 3️. Lock del Jugador Comprador
    # -----------------------------------------------------
    result_jugador = await db.execute(
        select(Jugador)
        .where(Jugador.id == tx.jugador_id)
        .with_for_update()
    )
    jugador = result_jugador.scalars().first()

    if not jugador:
        raise HTTPException(status_code=404, detail="Jugador no encontrado.")

    # -----------------------------------------------------
    # 4️. Cálculo Monetario Estricto (Decimal Seguro)
    # -----------------------------------------------------
    monto_total = Decimal(str(tx.monto_total)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # -----------------------------------------------------
    # 5️. Actualizaciones Centrales
    # -----------------------------------------------------

    # Marcar transacción como confirmada
    tx.estado_pago = "confirmado"

    # Acumular dinero al fondo global
    temporada.fondo_global = (
        Decimal(str(temporada.fondo_global)) + monto_total
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Inyectar calorías compradas
    jugador.calorias_compradas += tx.calorias_adquiridas
    jugador.calorias_balance_disponible += tx.calorias_adquiridas

    # -----------------------------------------------------
    # 6️. Evento Base: Compra de Calorías
    # -----------------------------------------------------
    evento_compra = EventoFeed(
        tipo_evento="compra_calorias",
        jugador_origen_id=jugador.id,
        metadata_json={
            "jugador_id": str(jugador.id),
            "nombre": jugador.nombre,
            "calorias_adquiridas": tx.calorias_adquiridas,
            "monto": str(monto_total),
            "mensaje": f"{jugador.nombre} adquirió {tx.calorias_adquiridas} calorías."
        }
    )
    db.add(evento_compra)

    eventos_ws.append({
        "evento": "compra_calorias",
        "data": evento_compra.metadata_json
    })

    # -----------------------------------------------------
    # 7️. Lógica de Desbloqueo (Solo si era pago_deuda)
    # -----------------------------------------------------
    desbloqueado = False

    if (
        tx.tipo_operacion == "pago_deuda"
        and jugador.estado == EstadoJugador.deudor
    ):
        jugador.estado = EstadoJugador.activo
        jugador.deuda_actual_monto = Decimal("0.00")
        jugador.deuda_actual_semana_id = None
        desbloqueado = True

        evento_desbloqueo = EventoFeed(
            tipo_evento="jugador_desbloqueado",
            jugador_origen_id=jugador.id,
            metadata_json={
                "jugador_id": str(jugador.id),
                "nombre": jugador.nombre,
                "mensaje": f"{jugador.nombre} pagó su deuda y vuelve a la competencia."
            }
        )
        db.add(evento_desbloqueo)

        eventos_ws.append({
            "evento": "jugador_desbloqueado",
            "data": evento_desbloqueo.metadata_json
        })

    # -----------------------------------------------------
    # 8️. Resultado Final (Sin Commit, Sin WS)
    # -----------------------------------------------------
    return {
        "status": "ejecutado",
        "monto_total": str(monto_total),
        "calorias_inyectadas": tx.calorias_adquiridas,
        "fondo_global_actual": str(temporada.fondo_global),
        "desbloqueo_ejecutado": desbloqueado,
        "eventos_ws": eventos_ws
    }