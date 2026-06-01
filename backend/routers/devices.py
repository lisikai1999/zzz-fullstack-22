from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Device, HealthRecord, RulEstimate
from schemas import DeviceCreate, DeviceOut, DeviceOverview

router = APIRouter()


@router.get("", response_model=list[DeviceOut])
def list_devices(db: Session = Depends(get_db)):
    devices = db.query(Device).all()
    result = []
    for d in devices:
        health = (
            db.query(HealthRecord)
            .filter(HealthRecord.device_id == d.id)
            .order_by(HealthRecord.calculated_at.desc())
            .first()
        )
        rul = (
            db.query(RulEstimate)
            .filter(RulEstimate.device_id == d.id)
            .order_by(RulEstimate.estimated_at.desc())
            .first()
        )
        result.append(
            DeviceOut(
                id=d.id,
                name=d.name,
                device_type=d.device_type,
                location=d.location,
                install_date=d.install_date,
                status=d.status,
                health_score=health.health_score if health else None,
                rul_days=rul.estimated_rul_days if rul else None,
            )
        )
    return result


@router.get("/overview", response_model=DeviceOverview)
def device_overview(db: Session = Depends(get_db)):
    devices = db.query(Device).all()
    total = len(devices)
    active = sum(1 for d in devices if d.status == "active")
    warning = sum(1 for d in devices if d.status == "warning")
    critical = sum(1 for d in devices if d.status == "critical")

    worst = []
    for d in devices:
        if d.status in ("warning", "critical"):
            health = (
                db.query(HealthRecord)
                .filter(HealthRecord.device_id == d.id)
                .order_by(HealthRecord.calculated_at.desc())
                .first()
            )
            rul = (
                db.query(RulEstimate)
                .filter(RulEstimate.device_id == d.id)
                .order_by(RulEstimate.estimated_at.desc())
                .first()
            )
            worst.append(
                DeviceOut(
                    id=d.id,
                    name=d.name,
                    device_type=d.device_type,
                    location=d.location,
                    install_date=d.install_date,
                    status=d.status,
                    health_score=health.health_score if health else None,
                    rul_days=rul.estimated_rul_days if rul else None,
                )
            )
    worst.sort(key=lambda x: x.health_score or 999)

    return DeviceOverview(
        total=total, active=active, warning=warning, critical=critical, worst_devices=worst
    )


@router.get("/{device_id}", response_model=DeviceOut)
def get_device(device_id: int, db: Session = Depends(get_db)):
    d = db.query(Device).filter(Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Device not found")
    health = (
        db.query(HealthRecord)
        .filter(HealthRecord.device_id == device_id)
        .order_by(HealthRecord.calculated_at.desc())
        .first()
    )
    rul = (
        db.query(RulEstimate)
        .filter(RulEstimate.device_id == device_id)
        .order_by(RulEstimate.estimated_at.desc())
        .first()
    )
    return DeviceOut(
        id=d.id,
        name=d.name,
        device_type=d.device_type,
        location=d.location,
        install_date=d.install_date,
        status=d.status,
        health_score=health.health_score if health else None,
        rul_days=rul.estimated_rul_days if rul else None,
    )


@router.post("", response_model=DeviceOut)
def create_device(device: DeviceCreate, db: Session = Depends(get_db)):
    d = Device(**device.model_dump())
    db.add(d)
    db.commit()
    db.refresh(d)
    return DeviceOut(
        id=d.id,
        name=d.name,
        device_type=d.device_type,
        location=d.location,
        install_date=d.install_date,
        status=d.status,
    )
