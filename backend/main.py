from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, SessionLocal
from models import Base
from routers import devices, sensors, anomalies, health, rul, workorders


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        from models import Device
        count = db.query(Device).count()
        if count == 0:
            from seed import seed_all
            seed_all(db)
    finally:
        db.close()
    yield


app = FastAPI(title="Predictive Maintenance System", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(devices.router, prefix="/api/devices", tags=["devices"])
app.include_router(sensors.router, prefix="/api/sensors", tags=["sensors"])
app.include_router(anomalies.router, prefix="/api/anomalies", tags=["anomalies"])
app.include_router(health.router, prefix="/api/health", tags=["health"])
app.include_router(rul.router, prefix="/api/rul", tags=["rul"])
app.include_router(workorders.router, prefix="/api/workorders", tags=["workorders"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
