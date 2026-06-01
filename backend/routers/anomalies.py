from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Anomaly
from schemas import AnomalyOut

router = APIRouter()


@router.get("", response_model=list[AnomalyOut])
def list_anomalies(
    device_id: int | None = None,
    severity: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(default=100, le=1000),
    db: Session = Depends(get_db),
):
    q = db.query(Anomaly)
    if device_id:
        q = q.filter(Anomaly.device_id == device_id)
    if severity:
        q = q.filter(Anomaly.severity == severity)
    if start:
        q = q.filter(Anomaly.detected_at >= start)
    if end:
        q = q.filter(Anomaly.detected_at <= end)
    return q.order_by(Anomaly.detected_at.desc()).limit(limit).all()


@router.get("/{device_id}", response_model=list[AnomalyOut])
def device_anomalies(
    device_id: int,
    limit: int = Query(default=100, le=1000),
    db: Session = Depends(get_db),
):
    return (
        db.query(Anomaly)
        .filter(Anomaly.device_id == device_id)
        .order_by(Anomaly.detected_at.desc())
        .limit(limit)
        .all()
    )
