# 5. core/scheduler.py (Final)

import logging
from datetime import datetime
import pytz

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.domain import SemanaTemporada, Temporada
from app.services.weekly_closure import ejecutar_cierre_semanal
from app.api.websockets import manager

logger = logging.getLogger(__name__)

# Zona horaria operativa (solo para lógica de negocio de día)
TZ_MEXICO = pytz.timezone("America/Mexico_City")


async def check_and_run_weekly_closure():
    """
    Orquestador automático del cierre semanal.

    Se ejecuta cada 10 minutos y solo procede si:

    1) Es lunes en zona horaria México
    2) Existe semana abierta vinculada a temporada activa
    3) fecha_fin (UTC) ya venció

    Reglas:
    - BD siempre en UTC
    - Evaluación de día en zona México
    - Commit explícito
    - WebSockets solo post-commit
    - Idempotente y seguro en escalamiento horizontal
    """

    # -----------------------------------------------------
    # 1️. Validación de día operativo (México)
    # -----------------------------------------------------
    now_mx = datetime.now(TZ_MEXICO)

    # 0 = Monday en Python
    if now_mx.weekday() != 0:
        return

    # -----------------------------------------------------
    # 2️. Crear sesión aislada para el scheduler
    # -----------------------------------------------------
    async with AsyncSessionLocal() as db:
        try:

            # -------------------------------------------------
            # 3️. Verificación ligera (sin lock)
            # -------------------------------------------------
            result = await db.execute(
                select(SemanaTemporada)
                .join(Temporada, Temporada.id == SemanaTemporada.temporada_id)
                .where(
                    SemanaTemporada.estado == "abierta",
                    Temporada.estado == "activa"
                )
            )

            semana_abierta = result.scalars().first()

            # Si no hay semana abierta, nada que hacer
            if not semana_abierta:
                return

            # -------------------------------------------------
            # 4️. Validación de vencimiento (UTC estricto)
            # -------------------------------------------------
            # CRÍTICO:
            # Todas las fechas en BD están en UTC.
            # Nunca mezclar con now_mx.
            now_utc = datetime.utcnow()

            if semana_abierta.fecha_fin > now_utc:
                return

            # -------------------------------------------------
            # 5️. Ejecutar cierre transaccional
            # -------------------------------------------------
            logger.info("Scheduler: Condiciones cumplidas. Iniciando cierre semanal...")

            resultados = await ejecutar_cierre_semanal(db)
            eventos_ws = resultados.get("eventos_ws", [])

            # -------------------------------------------------
            # 6️. Commit explícito
            # -------------------------------------------------
            await db.commit()

            logger.info("Scheduler: Cierre semanal persistido correctamente.")

            # -------------------------------------------------
            # 7️. Emisión WebSockets post-commit
            # -------------------------------------------------
            for evento in eventos_ws:
                try:
                    await manager.broadcast(evento)
                except Exception as ws_error:
                    # No revertimos la operación financiera por fallo de WS
                    logger.warning(f"Scheduler WS error (no crítico): {ws_error}")

        except Exception as e:
            await db.rollback()
            logger.error(f"Scheduler error crítico durante cierre semanal: {str(e)}")


# ---------------------------------------------------------
# 8️. Instancia global del scheduler
# ---------------------------------------------------------

scheduler = AsyncIOScheduler(timezone=TZ_MEXICO)

# Ejecuta cada 10 minutos
scheduler.add_job(
    check_and_run_weekly_closure,
    trigger="interval",
    minutes=10,
    id="weekly_closure_job",
    replace_existing=True
)