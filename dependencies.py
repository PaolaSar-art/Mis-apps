from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.domain import Jugador, EstadoJugador


# ---------------------------------------------------
# MOCK AUTH (Temporal)
# ---------------------------------------------------
# Simula usuario logueado mientras no existe login real.
# Luego será reemplazado por JWT.

async def get_current_user_id() -> str:
    """
    Simulación temporal de autenticación.
    En producción vendrá del JWT.
    """
    # ⚠️ luego será dinámico
    return "00000000-0000-0000-0000-000000000001"


# ---------------------------------------------------
# Obtener Jugador Actual
# ---------------------------------------------------

async def get_current_jugador(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> Jugador:

    result = await db.execute(
        select(Jugador).where(Jugador.id == user_id)
    )

    jugador = result.scalars().first()

    if not jugador:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jugador no encontrado"
        )

    return jugador


# ---------------------------------------------------
# Validación de Jugador Activo
# ---------------------------------------------------

async def require_jugador_activo(
    jugador: Jugador = Depends(get_current_jugador),
) -> Jugador:

    if jugador.estado == EstadoJugador.deudor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta congelada. Liquida tu deuda para continuar."
        )

    return jugador