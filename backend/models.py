from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Text, Index
from sqlalchemy.sql import func

from database import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    device_type = Column(String(50), nullable=False)
    location = Column(String(100), nullable=False)
    install_date = Column(Date, nullable=False)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, server_default=func.now())


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, nullable=False, index=True)
    sensor_type = Column(String(30), nullable=False)
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_readings_device_sensor_time", "device_id", "sensor_type", "timestamp"),
    )


class Anomaly(Base):
    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, nullable=False, index=True)
    sensor_type = Column(String(30), nullable=False)
    detection_method = Column(String(20), nullable=False)
    value = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    severity = Column(String(10), nullable=False)
    detected_at = Column(DateTime, nullable=False)


class HealthRecord(Base):
    __tablename__ = "health_records"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, nullable=False, index=True)
    health_score = Column(Float, nullable=False)
    temperature_score = Column(Float)
    vibration_score = Column(Float)
    current_score = Column(Float)
    calculated_at = Column(DateTime, nullable=False)


class RulEstimate(Base):
    __tablename__ = "rul_estimates"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, nullable=False, index=True)
    estimated_rul_days = Column(Float)
    fit_method = Column(String(20), nullable=False)
    r_squared = Column(Float, nullable=False)
    confidence_lower = Column(Float)
    confidence_upper = Column(Float)
    failure_threshold = Column(Float, nullable=False)
    estimated_at = Column(DateTime, nullable=False)


class WorkOrder(Base):
    __tablename__ = "work_orders"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    priority = Column(String(10), nullable=False)
    status = Column(String(20), default="open")
    trigger_type = Column(String(30))
    assigned_to = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime)
    completed_at = Column(DateTime)
