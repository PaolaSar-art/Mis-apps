# app/api/endpoints/ejercicio.py

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import require_jugador_activo
from app.models.domain import Jugador
from app.schemas.ejercicio import EjercicioCreate
print("ANTES DEL IMPORT SERVICE")
from app.services.exercise_service import registrar_ejercicio
print("DESPUES DEL IMPORT SERVICE")
from app.api.websockets import manager

router = APIRouter()


@router.post("/")
@router.post("")
async def registrar_ejercicio_endpoint(
    payload: EjercicioCreate,
    jugador: Jugador = Depends(require_jugador_activo),
    db: AsyncSession = Depends(get_db),
):
    
    resultado = await registrar_ejercicio(
        calorias=payload.calorias,
        jugador=jugador,
        db=db
    )

    await db.commit()

    await manager.broadcast(resultado["evento_ws"])

    return {
        "mensaje": resultado["mensaje"],
        "total_semana": resultado["total_semana"]
    }