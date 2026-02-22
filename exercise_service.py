# app/services/exercise_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from datetime import datetime

from app.models.domain import (
    Jugador,
    SemanaTemporada,
    Temporada,
    EstadisticaSemanal,
    EventoFeed
)


async def registrar_ejercicio(
    calorias: int,
    jugador: Jugador,
    db: AsyncSession
):
    """
    Registra calorías de ejercicio del jugador actual.
    """

    if calorias <= 0:
        raise HTTPException(status_code=400, detail="Calorías inválidas")

    # ---------------------------------------------------
    # Obtener semana activa
    # ---------------------------------------------------
    result = await db.execute(
        select(SemanaTemporada)
        .join(Temporada, Temporada.id == SemanaTemporada.temporada_id)
        .where(
            SemanaTemporada.estado == "abierta",
            Temporada.estado == "activa"
        )
    )

    semana = result.scalars().first()

    if not semana:
        raise HTTPException(status_code=400, detail="No hay semana activa")

    # ---------------------------------------------------
    # Obtener estadísticas del jugador en la semana
    # ---------------------------------------------------
    result = await db.execute(
        select(EstadisticaSemanal).where(
            EstadisticaSemanal.jugador_id == jugador.id,
            EstadisticaSemanal.semana_id == semana.id
        )
    )

    stats = result.scalars().first()

    if not stats:
        raise HTTPException(
            status_code=404,
            detail="Estadística semanal no encontrada"
        )

    # ---------------------------------------------------
    # Actualizar calorías
    # ---------------------------------------------------
    stats.calorias_ejercicio_semana += calorias
    jugador.calorias_ejercicio_total += calorias

    # ---------------------------------------------------
    # Crear evento feed
    # ---------------------------------------------------
    evento = EventoFeed(
        tipo_evento="ejercicio_registrado",
        jugador_origen_id=jugador.id,
        metadata_json={
            "jugador": jugador.nombre,
            "calorias": calorias,
            "mensaje": f"{jugador.nombre} quemó {calorias} calorías 🔥"
        }
    )

    db.add(evento)

    return {
        "mensaje": "Ejercicio registrado",
        "calorias_sumadas": calorias,
        "total_semana": stats.calorias_ejercicio_semana,
        "evento_ws": {
            "evento": "ejercicio_registrado",
            "data": evento.metadata_json
        }
    }