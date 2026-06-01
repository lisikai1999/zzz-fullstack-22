from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import Device, HealthRecord, RulEstimate
from schemas import RulEstimateOut, RulCurveOut
from services.rul_estimation import estimate_rul, generate_prediction_curve

router = APIRouter()


def _get_health_history(device_id: int, db: Session) -> list[dict]:
    records = (
        db.query(HealthRecord)
        .filter(HealthRecord.device_id == device_id)
        .order_by(HealthRecord.calculated_at)
        .all()
    )
    device = db.query(Device).filter(Device.id == device_id).first()
    if not records or not device:
        return []

    return [
        {
            "days_since_install": (r.calculated_at.date() - device.install_date).days,
            "health_score": r.health_score,
        }
        for r in records
    ]


@router.get("/{device_id}", response_model=RulEstimateOut | None)
def get_rul(device_id: int, db: Session = Depends(get_db)):
    rul = (
        db.query(RulEstimate)
        .filter(RulEstimate.device_id == device_id)
        .order_by(RulEstimate.estimated_at.desc())
        .first()
    )
    if not rul:
        return None
    return rul


@router.post("/estimate/{device_id}")
def estimate_device_rul(device_id: int, db: Session = Depends(get_db)):
    history = _get_health_history(device_id, db)
    result = estimate_rul(history)

    if result.get("estimated_rul_days") is not None:
        record = RulEstimate(
            device_id=device_id,
            estimated_rul_days=result["estimated_rul_days"],
            fit_method=result["fit_method"],
            r_squared=result["r_squared"],
            confidence_lower=result.get("confidence_lower"),
            confidence_upper=result.get("confidence_upper"),
            failure_threshold=result["failure_threshold"],
            estimated_at=datetime.now(),
        )
        db.add(record)
        db.commit()

    return result


@router.get("/{device_id}/curve", response_model=RulCurveOut)
def get_rul_curve(device_id: int, db: Session = Depends(get_db)):
    history = _get_health_history(device_id, db)
    return generate_prediction_curve(history)
