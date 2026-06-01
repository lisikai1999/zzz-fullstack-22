RULES = [
    {"name": "critical_health", "health_max": 20, "rul_max": 3, "priority": "critical"},
    {"name": "high_health", "health_max": 40, "rul_max": 7, "priority": "high"},
    {"name": "medium_health", "health_max": 60, "rul_max": 14, "priority": "medium"},
]

ANOMALY_BURST_THRESHOLD = 5
PRIORITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def evaluate_triggers(
    device_id: int,
    health_score: float,
    rul_days: float | None,
    recent_anomaly_count: int,
    existing_open_orders: list[dict],
) -> dict | None:
    existing_priorities = {
        wo["priority"]
        for wo in existing_open_orders
        if wo["status"] in ("open", "assigned", "in_progress")
    }
    max_existing_rank = max(
        (PRIORITY_RANK.get(p, 0) for p in existing_priorities), default=0
    )

    for rule in RULES:
        triggered = False
        trigger_type = ""

        if health_score <= rule["health_max"]:
            triggered = True
            trigger_type = "health_threshold"
        elif rul_days is not None and rul_days <= rule["rul_max"]:
            triggered = True
            trigger_type = "rul_critical"

        if triggered:
            if PRIORITY_RANK[rule["priority"]] > max_existing_rank:
                return {
                    "device_id": device_id,
                    "priority": rule["priority"],
                    "trigger_type": trigger_type,
                    "title": f"Auto: {rule['priority'].upper()} maintenance - {rule['name']}",
                    "description": (
                        f"Health score: {health_score:.1f}, "
                        f"RUL: {rul_days:.1f} days. "
                        f"Rule triggered: {rule['name']}"
                        if rul_days is not None
                        else f"Health score: {health_score:.1f}. Rule triggered: {rule['name']}"
                    ),
                }
            break

    if recent_anomaly_count >= ANOMALY_BURST_THRESHOLD:
        if PRIORITY_RANK["high"] > max_existing_rank:
            return {
                "device_id": device_id,
                "priority": "high",
                "trigger_type": "anomaly_burst",
                "title": "Auto: Anomaly burst detected",
                "description": f"{recent_anomaly_count} anomalies in last 24h. Immediate inspection recommended.",
            }

    return None
