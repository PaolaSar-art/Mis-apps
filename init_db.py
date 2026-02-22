import asyncio
from app.core.database import engine, Base

# IMPORTANTE: importa modelos para registrarlos
import app.models.domain


async def init_db():
    print("Creando tablas...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("Tablas creadas correctamente ✅")


if __name__ == "__main__":
    asyncio.run(init_db())