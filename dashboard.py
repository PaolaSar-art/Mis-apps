from fastapi import APIRouter, Depends
from app.api.dependencies import get_current_jugador
from app.models.domain import Jugador

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard(
    jugador: Jugador = Depends(get_current_jugador),
):
    return {
        "jugador": jugador.nombre,
        "estado": jugador.estado.value,
        "racha_actual": jugador.racha_actual,
        "calorias_totales": jugador.calorias_ejercicio_total,
        "saldo_wallet": float(jugador.saldo_wallet),
    }