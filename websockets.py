# 7. api/websockets.py

import json
import logging
from typing import List
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Gestiona conexiones WebSocket activas.

    - Mantiene lista de conexiones vivas
    - Limpia conexiones muertas automáticamente
    - No bloquea si una conexión falla
    """

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket conectado. Total activos: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket desconectado. Total activos: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """
        Envía mensaje JSON a todas las conexiones activas.
        Si alguna conexión falla, se elimina sin afectar a las demás.
        """
        if not self.active_connections:
            return

        payload = json.dumps(message)
        dead_connections = []

        for connection in self.active_connections:
            try:
                await connection.send_text(payload)
            except Exception as e:
                logger.warning(f"WebSocket muerto detectado: {e}")
                dead_connections.append(connection)

        # Limpieza de conexiones caídas
        for dead in dead_connections:
            self.disconnect(dead)


# Instancia global única
manager = ConnectionManager()
