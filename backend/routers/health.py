from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Device, SensorReading, HealthRecord
from schemas import HealthRecordOut, HealthHeatmapItem
from services.health_score import compute_health_score

router = APIRouter()


@router.get("/heatmap", response_model=list[HealthHeatmapItem])
def health_heatmap(db: Session = Depends(get_db)):
    devices = db.query(Device).all()
    result = []
    for d in devices:
        health = (
            db.query(HealthRecord)
            .filter(HealthRecord.device_id == d.id)
            .order_by(HealthRecord.calculated_at.desc())
            .first()
        )
        result.append(
            HealthHeatmapItem(
                device_id=d.id,
                name=d.name,
                device_type=d.device_type,
                location=d.location,
                health_score=health.health_score if health else 100.0,
                status=d.status,
            )
        )
    return result


@router.get("/{device_id}", response_model=list[HealthRecordOut])
def health_history(
    device_id: int,
    limit: int = Query(default=100, le=1000),
    db: Session = Depends(get_db),
):
    return (
        db.query(HealthRecord)
        .filter(HealthRecord.device_id == device_id)
        .order_by(HealthRecord.calculated_at.desc())
        .limit(limit)
        .all()
    )


@router.post("/calculate/{device_id}")
def calculate_health(device_id: int, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == device_id).first()
    sensor_data = {}
    for st in ("temperature", "vibration", "current"):
        readings = (
            db.query(SensorReading)
            .filter(
                SensorReading.device_id == device_id,
                SensorReading.sensor_type == st,
            )
            .order_by(SensorReading.timestamp.desc())
            .limit(200)
            .all()
        )
        sensor_data[st] = [r.value for r in reversed(readings)]

    scores = compute_health_score(device.device_type, sensor_data)

    record = HealthRecord(
        device_id=device_id,
        health_score=scores["health_score"],
        temperature_score=scores["temperature_score"],
        vibration_score=scores["vibration_score"],
        current_score=scores["current_score"],
        calculated_at=datetime.now(),
    )
    db.add(record)

    # Update device status
    if scores["health_score"] < 30:
        device.status = "critical"
    elif scores["health_score"] < 60:
        device.status = "warning"
    else:
        device.status = "active"

    db.commit()
    return scores
