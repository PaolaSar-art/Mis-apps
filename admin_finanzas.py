# 6. api/endpoints/admin_finanzas.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import logging

from app.core.database import get_db
from app.api.websockets import manager
from app.services.transactions import confirmar_transaccion

router = APIRouter(prefix="/api/v1/admin/transacciones")

@router.post("/{tx_id}/confirmar")
async def confirmar_pago_endpoint(
    tx_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    try:
        resultados = await confirmar_transaccion(tx_id=tx_id, db=db)
        eventos_ws = resultados.pop("eventos_ws", [])

        await db.commit()

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    for evento in eventos_ws:
        await manager.broadcast(evento)

    return jsonable_encoder({
        "mensaje": "Transacción confirmada con éxito.",
        "detalle": resultados
    })