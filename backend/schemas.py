from datetime import datetime, date
from pydantic import BaseModel


class DeviceCreate(BaseModel):
    name: str
    device_type: str
    location: str
    install_date: date


class DeviceOut(BaseModel):
    id: int
    name: str
    device_type: str
    location: str
    install_date: date
    status: str
    health_score: float | None = None
    rul_days: float | None = None

    class Config:
        from_attributes = True


class DeviceOverview(BaseModel):
    total: int
    active: int
    warning: int
    critical: int
    worst_devices: list[DeviceOut]


class SensorReadingIn(BaseModel):
    sensor_type: str
    value: float
    timestamp: datetime


class SensorBatchIn(BaseModel):
    device_id: int
    readings: list[SensorReadingIn]


class SensorReadingOut(BaseModel):
    sensor_type: str
    value: float
    timestamp: datetime

    class Config:
        from_attributes = True


class AnomalyOut(BaseModel):
    id: int
    device_id: int
    sensor_type: str
    detection_method: str
    value: float
    threshold: float
    severity: str
    detected_at: datetime

    class Config:
        from_attributes = True


class HealthRecordOut(BaseModel):
    id: int
    device_id: int
    health_score: float
    temperature_score: float | None
    vibration_score: float | None
    current_score: float | None
    calculated_at: datetime

    class Config:
        from_attributes = True


class HealthHeatmapItem(BaseModel):
    device_id: int
    name: str
    device_type: str
    location: str
    health_score: float
    status: str


class RulEstimateOut(BaseModel):
    device_id: int
    estimated_rul_days: float | None
    fit_method: str
    r_squared: float
    confidence_lower: float | None
    confidence_upper: float | None
    failure_threshold: float
    estimated_at: datetime

    class Config:
        from_attributes = True


class RulCurveOut(BaseModel):
    historical: list[dict]
    predicted: list[dict]
    confidence_upper: list[dict]
    confidence_lower: list[dict]
    failure_threshold: float


class WorkOrderCreate(BaseModel):
    device_id: int
    title: str
    description: str | None = None
    priority: str = "medium"


class WorkOrderUpdate(BaseModel):
    status: str | None = None
    assigned_to: str | None = None


class WorkOrderOut(BaseModel):
    id: int
    device_id: int
    title: str
    description: str | None
    priority: str
    status: str
    trigger_type: str | None
    assigned_to: str | None
    created_at: datetime
    updated_at: datetime | None
    completed_at: datetime | None

    class Config:
        from_attributes = True
