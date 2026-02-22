import asyncio
from datetime import datetime, timedelta
from app.core.database import AsyncSessionLocal
from app.models.domain import (
    Temporada,
    SemanaTemporada,
    Jugador
)

async def seed():

    async with AsyncSessionLocal() as db:

        temporada = Temporada(
            nombre="Temporada Inicial"
        )

        db.add(temporada)
        await db.flush()

        semana = SemanaTemporada(
            temporada_id=temporada.id,
            numero_semana=1,
            fecha_inicio=datetime.utcnow(),
            fecha_fin=datetime.utcnow() + timedelta(days=7)
        )

        db.add(semana)

        jugadores = [
            Jugador(nombre="Ana", genero="F"),
            Jugador(nombre="Carlos", genero="M"),
            Jugador(nombre="Luis", genero="M"),
        ]

        db.add_all(jugadores)

        await db.commit()

    print("Seed ejecutado ✅")

if __name__ == "__main__":
    asyncio.run(seed())