from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models import SensorReading, Anomaly, Device
from schemas import SensorBatchIn, SensorReadingOut
from services.anomaly_detection import detect_anomalies

router = APIRouter()


@router.post("/readings")
def ingest_readings(batch: SensorBatchIn, db: Session = Depends(get_db)):
    records = []
    for r in batch.readings:
        record = SensorReading(
            device_id=batch.device_id,
            sensor_type=r.sensor_type,
            value=r.value,
            timestamp=r.timestamp,
        )
        records.append(record)
    db.add_all(records)
    db.commit()

    # Run anomaly detection per sensor type
    anomalies_found = 0
    sensor_types = set(r.sensor_type for r in batch.readings)
    for st in sensor_types:
        readings = (
            db.query(SensorReading)
            .filter(
                SensorReading.device_id == batch.device_id,
                SensorReading.sensor_type == st,
            )
            .order_by(SensorReading.timestamp)
            .limit(500)
            .all()
        )
        values = [r.value for r in readings]
        detected = detect_anomalies(values, window_size=100, ewma_span=30)

        new_timestamps = {r.timestamp for r in batch.readings if r.sensor_type == st}
        for anom in detected:
            idx = anom["index"]
            if idx < len(readings) and readings[idx].timestamp in new_timestamps:
                anomaly_record = Anomaly(
                    device_id=batch.device_id,
                    sensor_type=st,
                    detection_method=anom["method"],
                    value=anom["value"],
                    threshold=anom.get("threshold", 0),
                    severity=anom["severity"],
                    detected_at=readings[idx].timestamp,
                )
                db.add(anomaly_record)
                anomalies_found += 1

    if anomalies_found > 0:
        db.commit()

    return {"ingested": len(records), "anomalies_detected": anomalies_found}


@router.post("/readings/bulk")
def ingest_bulk(batches: list[SensorBatchIn], db: Session = Depends(get_db)):
    total = 0
    for batch in batches:
        for r in batch.readings:
            record = SensorReading(
                device_id=batch.device_id,
                sensor_type=r.sensor_type,
                value=r.value,
                timestamp=r.timestamp,
            )
            db.add(record)
            total += 1
    db.commit()
    return {"ingested": total}


@router.get("/readings/{device_id}", response_model=list[SensorReadingOut])
def get_readings(
    device_id: int,
    sensor_type: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(default=2000, le=10000),
    db: Session = Depends(get_db),
):
    q = db.query(SensorReading).filter(SensorReading.device_id == device_id)
    if sensor_type:
        q = q.filter(SensorReading.sensor_type == sensor_type)
    if start:
        q = q.filter(SensorReading.timestamp >= start)
    if end:
        q = q.filter(SensorReading.timestamp <= end)
    q = q.order_by(SensorReading.timestamp.desc()).limit(limit)
    return q.all()
