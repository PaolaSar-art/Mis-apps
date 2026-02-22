# 4. services/weekly_closure.py (Final Blindado)

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.models.domain import (
    Jugador,
    SemanaTemporada,
    Temporada,
    EstadisticaSemanal,
    CacheRankingActual,
    EventoFeed,
    EstadoJugador
)

logger = logging.getLogger(__name__)


async def ejecutar_cierre_semanal(db: AsyncSession) -> dict:
    """
    Ejecuta el cierre disciplinario de la semana activa.

    Reglas:
    - Evalúa meta mínima (Mujer=800, Hombre=1000)
    - Genera deuda acumulativa exacta
    - Rompe racha si no cumple
    - Incrementa racha si cumple
    - Cierra semana actual
    - Crea nueva semana en UTC
    - Inicializa estadísticas en cero
    - Resetea cache_ranking_actual
    - Genera evento nueva_semana
    - NO hace commit
    - NO emite WebSockets
    """

    eventos_ws = []
    jugadores_bloqueados = []

    # -----------------------------------------------------
    # 1️. Lock Semana Activa (JOIN con temporada activa)
    # -----------------------------------------------------
    result_semana = await db.execute(
        select(SemanaTemporada)
        .join(Temporada, Temporada.id == SemanaTemporada.temporada_id)
        .where(
            SemanaTemporada.estado == "abierta",
            Temporada.estado == "activa"
        )
        .with_for_update()
    )

    semana_actual = result_semana.scalars().first()

    if not semana_actual:
        raise HTTPException(
            status_code=400,
            detail="No existe semana abierta vinculada a una temporada activa."
        )

    # -----------------------------------------------------
    # 2️. Lock Temporada Activa
    # -----------------------------------------------------
    result_temp = await db.execute(
        select(Temporada)
        .where(Temporada.id == semana_actual.temporada_id)
        .with_for_update()
    )
    temporada = result_temp.scalars().first()

    if not temporada:
        raise HTTPException(status_code=400, detail="Temporada activa no encontrada.")

    # -----------------------------------------------------
    # 3️. Lock Todos los Jugadores
    # -----------------------------------------------------
    result_jugadores = await db.execute(
        select(Jugador).with_for_update()
    )
    jugadores = result_jugadores.scalars().all()

    # -----------------------------------------------------
    # 4️. Lock Estadísticas de la Semana
    # -----------------------------------------------------
    result_stats = await db.execute(
        select(EstadisticaSemanal)
        .where(EstadisticaSemanal.semana_id == semana_actual.id)
        .with_for_update()
    )
    stats = result_stats.scalars().all()

    stats_map = {s.jugador_id: s for s in stats}

    # -----------------------------------------------------
    # 5️. Evaluación Disciplinaria
    # -----------------------------------------------------
    for jugador in jugadores:

        stat = stats_map.get(jugador.id)
        calorias_semana = stat.calorias_ejercicio_semana if stat else 0

        genero = jugador.genero.upper()
        es_mujer = genero in ["F", "MUJER"]

        meta = 800 if es_mujer else 1000

        if calorias_semana >= meta:
            # Cumplió meta → incrementa racha
            jugador.racha_actual += 1
        else:
            # No cumplió → penalización acumulativa
            deficit = meta - calorias_semana

            # Redondeo hacia arriba por bloques de 100
            bloques = (deficit + 99) // 100

            costo_por_bloque = 50 if es_mujer else 40
            multa_calculada = bloques * costo_por_bloque

            multa = Decimal(str(multa_calculada))

            # Acumulación estricta (funciona incluso si ya era deudor)
            jugador.deuda_actual_monto = (
                Decimal(str(jugador.deuda_actual_monto)) + multa
            )

            jugador.deuda_actual_semana_id = semana_actual.id
            jugador.estado = EstadoJugador.deudor
            jugador.racha_actual = 0

            jugadores_bloqueados.append(jugador.nombre)

            # Evento de bloqueo
            evento_bloqueo = EventoFeed(
                tipo_evento="jugador_bloqueado",
                jugador_origen_id=jugador.id,
                metadata_json={
                    "jugador_id": str(jugador.id),
                    "nombre": jugador.nombre,
                    "multa_generada": str(multa),
                    "calorias_faltantes": deficit,
                    "mensaje": f"{jugador.nombre} no alcanzó la meta y fue bloqueado con multa de ${multa}."
                }
            )

            db.add(evento_bloqueo)

            eventos_ws.append({
                "evento": "jugador_bloqueado",
                "data": evento_bloqueo.metadata_json
            })

    # -----------------------------------------------------
    # 6️. Cerrar Semana Actual
    # -----------------------------------------------------
    semana_actual.estado = "cerrada"

    # -----------------------------------------------------
    # 7️. Crear Nueva Semana (UTC)
    # -----------------------------------------------------
    now_utc = datetime.utcnow()

    nueva_semana = SemanaTemporada(
        temporada_id=temporada.id,
        numero_semana=semana_actual.numero_semana + 1,
        estado="abierta",
        fecha_inicio=now_utc,
        fecha_fin=now_utc + timedelta(days=7)
    )

    db.add(nueva_semana)
    await db.flush()  # Necesario para obtener nueva_semana.id

    # -----------------------------------------------------
    # 8️. Inicializar Estadísticas en Cero
    # -----------------------------------------------------
    for jugador in jugadores:
        db.add(
            EstadisticaSemanal(
                jugador_id=jugador.id,
                semana_id=nueva_semana.id,
                calorias_ejercicio_semana=0
            )
        )

    # -----------------------------------------------------
    # 9️. Reset Seguro de CacheRankingActual
    # -----------------------------------------------------
    await db.execute(
        delete(CacheRankingActual)
        .where(CacheRankingActual.semana_id == nueva_semana.id)
    )

    db.add(
        CacheRankingActual(
            semana_id=nueva_semana.id,
            jugador_id_lider=None
        )
    )

    # -----------------------------------------------------
    # 10. Evento Nueva Semana
    # -----------------------------------------------------
    evento_nueva_semana = EventoFeed(
        tipo_evento="nueva_semana",
        metadata_json={
            "numero_semana": nueva_semana.numero_semana,
            "mensaje": f"Inicia la semana {nueva_semana.numero_semana}. ¡Nueva batalla!"
        }
    )

    db.add(evento_nueva_semana)

    eventos_ws.append({
        "evento": "nueva_semana",
        "data": evento_nueva_semana.metadata_json
    })

    logger.info(
        f"Cierre ejecutado correctamente. Nueva semana: {nueva_semana.numero_semana}. "
        f"Jugadores bloqueados: {len(jugadores_bloqueados)}"
    )

    # -----------------------------------------------------
    # Resultado final (sin commit, sin WS)
    # -----------------------------------------------------
    return {
        "mensaje": "Cierre semanal ejecutado correctamente.",
        "nueva_semana": nueva_semana.numero_semana,
        "jugadores_bloqueados": jugadores_bloqueados,
        "eventos_ws": eventos_ws
    }
