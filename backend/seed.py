import math
import random
from datetime import date, datetime, timedelta

import numpy as np
from sqlalchemy.orm import Session

from models import Device, SensorReading, Anomaly, HealthRecord, RulEstimate, WorkOrder
from services.health_score import compute_health_score, NORMAL_RANGES
from services.rul_estimation import estimate_rul
from services.anomaly_detection import detect_anomalies
from services.maintenance_trigger import evaluate_triggers

DEVICE_FLEET = [
    ("CNC-PUMP-001", "pump", "A1"),
    ("CNC-PUMP-002", "pump", "A1"),
    ("CNC-PUMP-003", "pump", "A2"),
    ("HYD-PUMP-004", "pump", "A2"),
    ("HYD-PUMP-005", "pump", "B1"),
    ("COOL-PUMP-006", "pump", "B1"),
    ("COOL-PUMP-007", "pump", "B2"),
    ("FEED-PUMP-008", "pump", "B2"),
    ("SPIN-MOTOR-001", "motor", "A1"),
    ("SPIN-MOTOR-002", "motor", "A1"),
    ("CONV-MOTOR-003", "motor", "A2"),
    ("CONV-MOTOR-004", "motor", "A2"),
    ("DRIVE-MOTOR-005", "motor", "B1"),
    ("DRIVE-MOTOR-006", "motor", "B1"),
    ("LIFT-MOTOR-007", "motor", "B2"),
    ("AIR-COMP-001", "compressor", "A1"),
    ("AIR-COMP-002", "compressor", "A2"),
    ("AIR-COMP-003", "compressor", "B1"),
    ("REF-COMP-004", "compressor", "B2"),
    ("REF-COMP-005", "compressor", "B2"),
]

PATTERNS = {
    0: "healthy",
    1: "healthy",
    2: "healthy",
    3: "healthy",
    4: "healthy",
    5: "healthy",
    6: "healthy",
    7: "healthy",
    8: "linear_degradation",
    9: "linear_degradation",
    10: "linear_degradation",
    11: "linear_degradation",
    12: "linear_degradation",
    13: "exponential_degradation",
    14: "exponential_degradation",
    15: "exponential_degradation",
    16: "exponential_degradation",
    17: "critical",
    18: "critical",
    19: "recovered",
}


def generate_sensor_series(
    days: int,
    samples_per_day: int,
    pattern: str,
    normal_range: tuple[float, float],
    noise_std: float,
    seed: int = 0,
) -> list[float]:
    rng = np.random.default_rng(seed)
    low, high = normal_range
    center = (low + high) / 2
    total_samples = days * samples_per_day
    values = []

    for i in range(total_samples):
        day_frac = i / samples_per_day
        diurnal = math.sin(2 * math.pi * day_frac) * (high - low) * 0.03

        if pattern == "healthy":
            base = center + diurnal
            noise = rng.normal(0, noise_std)
            values.append(base + noise)

        elif pattern == "linear_degradation":
            drift = (day_frac / days) * (high - center) * 0.8
            base = center + drift + diurnal
            noise = rng.normal(0, noise_std * (1 + day_frac / days * 0.5))
            values.append(base + noise)

        elif pattern == "exponential_degradation":
            t_norm = day_frac / days
            drift = (math.exp(3 * t_norm) - 1) / (math.exp(3) - 1) * (high - center) * 1.2
            base = center + drift + diurnal
            noise = rng.normal(0, noise_std * (1 + t_norm))
            values.append(base + noise)

        elif pattern == "critical":
            base = high + (high - low) * 0.15 + diurnal
            noise = rng.normal(0, noise_std * 2)
            values.append(base + noise)

        elif pattern == "recovered":
            if day_frac < days * 0.7:
                drift = (day_frac / (days * 0.7)) * (high - center) * 0.7
                base = center + drift + diurnal
            else:
                base = center + diurnal
            noise = rng.normal(0, noise_std)
            values.append(base + noise)

    return values


def seed_all(db: Session):
    print("Seeding database with demo data...")
    base_date = date.today() - timedelta(days=120)
    start_datetime = datetime.combine(base_date, datetime.min.time())
    days = 90
    samples_per_day = 24  # hourly

    devices = []
    for i, (name, dtype, location) in enumerate(DEVICE_FLEET):
        install_date = base_date - timedelta(days=random.randint(180, 720))
        d = Device(
            name=name,
            device_type=dtype,
            location=location,
            install_date=install_date,
            status="active",
        )
        db.add(d)
        devices.append((d, PATTERNS[i], install_date))

    db.commit()

    for d, pattern, install_date in devices:
        db.refresh(d)
        ranges = NORMAL_RANGES.get(d.device_type, NORMAL_RANGES["motor"])

        all_sensor_data = {}
        for sensor_type in ("temperature", "vibration", "current"):
            sr = ranges[sensor_type]
            noise_std = (sr[1] - sr[0]) * 0.03
            series = generate_sensor_series(
                days=days,
                samples_per_day=samples_per_day,
                pattern=pattern,
                normal_range=sr,
                noise_std=noise_std,
                seed=d.id * 100 + hash(sensor_type) % 50,
            )
            all_sensor_data[sensor_type] = series

            readings = []
            for j, val in enumerate(series):
                ts = start_datetime + timedelta(hours=j)
                readings.append(
                    SensorReading(
                        device_id=d.id,
                        sensor_type=sensor_type,
                        value=round(val, 3),
                        timestamp=ts,
                    )
                )
            db.add_all(readings)

        db.commit()

        # Detect anomalies
        for sensor_type in ("temperature", "vibration", "current"):
            values = all_sensor_data[sensor_type]
            detected = detect_anomalies(values, window_size=100, ewma_span=30)
            for anom in detected[-10:]:  # keep last 10 per sensor
                ts = start_datetime + timedelta(hours=anom["index"])
                db.add(
                    Anomaly(
                        device_id=d.id,
                        sensor_type=sensor_type,
                        detection_method=anom["method"],
                        value=round(anom["value"], 3),
                        threshold=round(anom.get("threshold", 0), 3),
                        severity=anom["severity"],
                        detected_at=ts,
                    )
                )
        db.commit()

        # Compute health scores (weekly snapshots)
        health_history = []
        for week in range(0, days, 7):
            sample_end = min((week + 7) * samples_per_day, days * samples_per_day)
            sample_start = max(0, sample_end - 200)
            window_data = {
                st: all_sensor_data[st][sample_start:sample_end]
                for st in ("temperature", "vibration", "current")
            }
            scores = compute_health_score(d.device_type, window_data)
            calc_time = start_datetime + timedelta(days=week + 7)
            db.add(
                HealthRecord(
                    device_id=d.id,
                    health_score=scores["health_score"],
                    temperature_score=scores["temperature_score"],
                    vibration_score=scores["vibration_score"],
                    current_score=scores["current_score"],
                    calculated_at=calc_time,
                )
            )
            health_history.append(
                {
                    "days_since_install": (calc_time.date() - install_date).days,
                    "health_score": scores["health_score"],
                }
            )

        db.commit()

        # RUL estimation
        rul_result = estimate_rul(health_history)
        if rul_result.get("estimated_rul_days") is not None:
            db.add(
                RulEstimate(
                    device_id=d.id,
                    estimated_rul_days=rul_result["estimated_rul_days"],
                    fit_method=rul_result["fit_method"],
                    r_squared=rul_result["r_squared"],
                    confidence_lower=rul_result.get("confidence_lower"),
                    confidence_upper=rul_result.get("confidence_upper"),
                    failure_threshold=rul_result["failure_threshold"],
                    estimated_at=datetime.now(),
                )
            )

        # Update device status based on latest health
        if health_history:
            latest_health = health_history[-1]["health_score"]
            if latest_health < 30:
                d.status = "critical"
            elif latest_health < 60:
                d.status = "warning"
            else:
                d.status = "active"

        db.commit()

    # Generate work orders via trigger logic
    for d, pattern, _ in devices:
        db.refresh(d)
        latest_health = (
            db.query(HealthRecord)
            .filter(HealthRecord.device_id == d.id)
            .order_by(HealthRecord.calculated_at.desc())
            .first()
        )
        latest_rul = (
            db.query(RulEstimate)
            .filter(RulEstimate.device_id == d.id)
            .order_by(RulEstimate.estimated_at.desc())
            .first()
        )
        anomaly_count = (
            db.query(Anomaly)
            .filter(Anomaly.device_id == d.id)
            .count()
        )

        health_val = latest_health.health_score if latest_health else 100
        rul_val = latest_rul.estimated_rul_days if latest_rul else None

        trigger = evaluate_triggers(
            device_id=d.id,
            health_score=health_val,
            rul_days=rul_val,
            recent_anomaly_count=min(anomaly_count, 10),
            existing_open_orders=[],
        )
        if trigger:
            wo = WorkOrder(
                device_id=d.id,
                title=trigger["title"],
                description=trigger["description"],
                priority=trigger["priority"],
                status="open",
                trigger_type=trigger["trigger_type"],
            )
            db.add(wo)

    # Add a completed work order for recovered device
    recovered_device = devices[19][0]
    db.add(
        WorkOrder(
            device_id=recovered_device.id,
            title="Bearing replacement completed",
            description="Replaced worn bearings, device returned to normal operation.",
            priority="high",
            status="completed",
            trigger_type="health_threshold",
            assigned_to="Zhang Wei",
            completed_at=datetime.now() - timedelta(days=10),
            updated_at=datetime.now() - timedelta(days=10),
        )
    )

    db.commit()
    print(f"Seeded {len(devices)} devices with {days} days of data.")
