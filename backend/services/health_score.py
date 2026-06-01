import numpy as np

SENSOR_WEIGHTS = {
    "temperature": 0.35,
    "vibration": 0.40,
    "current": 0.25,
}

NORMAL_RANGES = {
    "pump": {
        "temperature": (40, 80),
        "vibration": (0.5, 4.0),
        "current": (10, 25),
    },
    "motor": {
        "temperature": (35, 75),
        "vibration": (0.3, 3.5),
        "current": (5, 20),
    },
    "compressor": {
        "temperature": (45, 90),
        "vibration": (1.0, 6.0),
        "current": (15, 40),
    },
}


def compute_sensor_score(
    values: list[float], normal_range: tuple[float, float], window: int = 50
) -> float:
    if not values:
        return 100.0

    recent = values[-window:]
    low, high = normal_range
    center = (low + high) / 2
    half_range = (high - low) / 2

    mean_val = np.mean(recent)
    std_val = np.std(recent)

    distance = abs(mean_val - center) / half_range
    base_score = max(0, 100 * (1 - distance))

    range_width = high - low
    variance_penalty = min(20, (std_val / range_width) * 40)

    trend_penalty = 0.0
    if len(recent) > 10:
        x = np.arange(len(recent))
        slope = np.polyfit(x, recent, 1)[0]
        trend_penalty = min(15, max(0, slope * len(recent) / range_width * 30))

    return max(0.0, min(100.0, base_score - variance_penalty - trend_penalty))


def compute_health_score(
    device_type: str, sensor_data: dict[str, list[float]]
) -> dict:
    ranges = NORMAL_RANGES.get(device_type, NORMAL_RANGES["motor"])
    scores = {}

    for sensor_type, weight in SENSOR_WEIGHTS.items():
        if sensor_type in sensor_data and len(sensor_data[sensor_type]) > 0:
            scores[sensor_type] = compute_sensor_score(
                sensor_data[sensor_type], ranges[sensor_type]
            )
        else:
            scores[sensor_type] = 100.0

    weighted_sum = sum(scores[s] * SENSOR_WEIGHTS[s] for s in SENSOR_WEIGHTS)

    min_score = min(scores.values())
    critical_penalty = max(0, (30 - min_score) * 0.5) if min_score < 30 else 0

    health_score = max(0.0, min(100.0, weighted_sum - critical_penalty))

    return {
        "health_score": round(health_score, 1),
        "temperature_score": round(scores["temperature"], 1),
        "vibration_score": round(scores["vibration"], 1),
        "current_score": round(scores["current"], 1),
    }
