# 8. main.py

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager
import logging

from fastapi.middleware.cors import CORSMiddleware

from app.core.scheduler import scheduler
from app.api.websockets import manager
from app.api.endpoints import dashboard, admin_finanzas

from app.api.endpoints import ejercicio

logger = logging.getLogger(__name__)


# ===============================
# LIFESPAN (Scheduler automático)
# ===============================
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando APScheduler...")
    scheduler.start()

    yield

    logger.info("Deteniendo APScheduler...")
    scheduler.shutdown()


# ===============================
# APP
# ===============================
app = FastAPI(
    title="Burn & Conquer API",
    version="1.0",
    lifespan=lifespan
)

# ===============================
# CORS (Frontend local)
# ===============================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # solo desarrollo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===============================
# ROUTERS (IMPORTANTE)
# ===============================

# Jugador (Dashboard / acciones usuario)
app.include_router(
    dashboard.router,
    prefix="/api/v1/jugador",
    tags=["Jugador"]
)

# Administración financiera
app.include_router(
    admin_finanzas.router,
    prefix="/api/v1/admin",
    tags=["Admin"]
)

# Registrar ejercicio
app.include_router(
    ejercicio.router,
    prefix="/api/v1/ejercicio",
    tags=["Ejercicio"]
)
# ===============================
# WEBSOCKET FEED
# ===============================
@app.websocket("/ws/feed")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)