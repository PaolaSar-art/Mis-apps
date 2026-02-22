# 2. models/domain.py

from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Enum, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import enum
import uuid
from app.core.database import Base
from decimal import Decimal
from sqlalchemy.orm import relationship

class EstadoJugador(enum.Enum):
    activo = "activo"
    deudor = "deudor"

class Temporada(Base):
    __tablename__ = "temporadas"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(String, nullable=False)
    fondo_global = Column(Numeric(10, 2), default=Decimal("0.00"))
    estado = Column(String, default="activa", index=True)
    fecha_inicio = Column(DateTime, default=datetime.utcnow)

class SemanaTemporada(Base):
    __tablename__ = "semanas_temporada"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temporada_id = Column(UUID(as_uuid=True), ForeignKey("temporadas.id"))
    numero_semana = Column(Integer, nullable=False)
    estado = Column(String, default="abierta")
    fecha_inicio = Column(DateTime, nullable=False)
    fecha_fin = Column(DateTime, nullable=False)

class Jugador(Base):
    __tablename__ = "jugadores"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(String, nullable=False)
    genero = Column(String, nullable=False)
    estado = Column(Enum(EstadoJugador), default=EstadoJugador.activo, index=True)

    calorias_ejercicio_total = Column(Integer, default=0)
    calorias_compradas = Column(Integer, default=0)
    calorias_balance_disponible = Column(Integer, default=0)

    saldo_wallet = Column(Numeric(10, 2), default=Decimal("0.00"))
    deuda_actual_monto = Column(Numeric(10, 2), default=Decimal("0.00"))
    deuda_actual_semana_id = Column(UUID(as_uuid=True), ForeignKey("semanas_temporada.id"), nullable=True)

    racha_actual = Column(Integer, default=0)
    transacciones = relationship("TransaccionFinanciera", back_populates="jugador")

class EstadisticaSemanal(Base):
    __tablename__ = "estadisticas_semanales"
    jugador_id = Column(UUID(as_uuid=True), ForeignKey("jugadores.id"), primary_key=True)
    semana_id = Column(UUID(as_uuid=True), ForeignKey("semanas_temporada.id"), primary_key=True)
    calorias_ejercicio_semana = Column(Integer, default=0)

class CacheRankingActual(Base):
    __tablename__ = "cache_ranking_actual"
    semana_id = Column(UUID(as_uuid=True), ForeignKey("semanas_temporada.id"), primary_key=True)
    jugador_id_lider = Column(UUID(as_uuid=True), ForeignKey("jugadores.id"), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class EventoFeed(Base):
    __tablename__ = "eventos_feed"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo_evento = Column(String, nullable=False)
    jugador_origen_id = Column(UUID(as_uuid=True), ForeignKey("jugadores.id"), nullable=True)
    metadata_json = Column(JSONB, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

# =====================================================
# MODELOS FINANCIEROS
# =====================================================

class TransaccionFinanciera(Base):
    __tablename__ = "transacciones_financieras"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    jugador_id = Column(
        UUID(as_uuid=True),
        ForeignKey("jugadores.id"),
        nullable=False
    )

    monto_total = Column(Numeric(10, 2), nullable=False)
    calorias_adquiridas = Column(Integer, default=0)

    tipo_operacion = Column(String, nullable=False)  
    # "pago_deuda" | "compra_voluntaria"

    estado_pago = Column(String, default="pendiente")
    # pendiente | confirmado

    created_at = Column(DateTime, default=datetime.utcnow)
    jugador = relationship("Jugador", back_populates="transacciones")

class DistribucionPago(Base):
    __tablename__ = "distribuciones_pagos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    transaccion_id = Column(
        UUID(as_uuid=True),
        ForeignKey("transacciones_financieras.id"),
        nullable=False
    )

    jugador_receptor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("jugadores.id"),
        nullable=False
    )

    monto_recibido = Column(Numeric(10, 2), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)