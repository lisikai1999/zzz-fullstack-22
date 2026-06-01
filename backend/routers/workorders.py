from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import WorkOrder, Device
from schemas import WorkOrderCreate, WorkOrderUpdate, WorkOrderOut

router = APIRouter()

VALID_STATUSES = {"open", "assigned", "in_progress", "completed", "cancelled"}
VALID_PRIORITIES = {"low", "medium", "high", "critical"}


@router.get("", response_model=list[WorkOrderOut])
def list_workorders(
    status: str | None = None,
    priority: str | None = None,
    device_id: int | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(WorkOrder)
    if status:
        q = q.filter(WorkOrder.status == status)
    if priority:
        q = q.filter(WorkOrder.priority == priority)
    if device_id:
        q = q.filter(WorkOrder.device_id == device_id)
    offset = (page - 1) * page_size
    return q.order_by(WorkOrder.created_at.desc()).offset(offset).limit(page_size).all()


@router.get("/count")
def count_workorders(
    status: str | None = None,
    priority: str | None = None,
    device_id: int | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(WorkOrder)
    if status:
        q = q.filter(WorkOrder.status == status)
    if priority:
        q = q.filter(WorkOrder.priority == priority)
    if device_id:
        q = q.filter(WorkOrder.device_id == device_id)
    return {"count": q.count()}


@router.get("/{workorder_id}", response_model=WorkOrderOut)
def get_workorder(workorder_id: int, db: Session = Depends(get_db)):
    wo = db.query(WorkOrder).filter(WorkOrder.id == workorder_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")
    return wo


@router.post("", response_model=WorkOrderOut)
def create_workorder(wo: WorkOrderCreate, db: Session = Depends(get_db)):
    if not wo.title or not wo.title.strip():
        raise HTTPException(status_code=422, detail="Title is required")
    if wo.priority not in VALID_PRIORITIES:
        raise HTTPException(status_code=422, detail=f"Priority must be one of: {VALID_PRIORITIES}")
    device = db.query(Device).filter(Device.id == wo.device_id).first()
    if not device:
        raise HTTPException(status_code=422, detail=f"Device {wo.device_id} does not exist")

    record = WorkOrder(
        device_id=wo.device_id,
        title=wo.title.strip(),
        description=wo.description,
        priority=wo.priority,
        status="open",
        trigger_type="manual",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.patch("/{workorder_id}", response_model=WorkOrderOut)
def update_workorder(
    workorder_id: int, update: WorkOrderUpdate, db: Session = Depends(get_db)
):
    wo = db.query(WorkOrder).filter(WorkOrder.id == workorder_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")
    if update.status:
        if update.status not in VALID_STATUSES:
            raise HTTPException(status_code=422, detail=f"Status must be one of: {VALID_STATUSES}")
        wo.status = update.status
        wo.updated_at = datetime.now()
    if update.assigned_to:
        wo.assigned_to = update.assigned_to
        wo.updated_at = datetime.now()
    db.commit()
    db.refresh(wo)
    return wo


@router.post("/{workorder_id}/complete", response_model=WorkOrderOut)
def complete_workorder(workorder_id: int, db: Session = Depends(get_db)):
    wo = db.query(WorkOrder).filter(WorkOrder.id == workorder_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")
    wo.status = "completed"
    wo.completed_at = datetime.now()
    wo.updated_at = datetime.now()
    db.commit()
    db.refresh(wo)
    return wo
