from services.maintenance_trigger import (
    evaluate_triggers,
    RULES,
    ANOMALY_BURST_THRESHOLD,
    PRIORITY_RANK,
)


class TestMaintenanceTrigger:
    def test_critical_health_trigger(self):
        result = evaluate_triggers(
            device_id=1,
            health_score=15.0,
            rul_days=10.0,
            recent_anomaly_count=0,
            existing_open_orders=[],
        )
        assert result is not None
        assert result["priority"] == "critical"
        assert result["trigger_type"] == "health_threshold"

    def test_critical_rul_trigger(self):
        result = evaluate_triggers(
            device_id=1,
            health_score=45.0,
            rul_days=2.0,
            recent_anomaly_count=0,
            existing_open_orders=[],
        )
        assert result is not None
        assert result["priority"] == "critical"
        assert result["trigger_type"] == "rul_critical"

    def test_high_trigger(self):
        result = evaluate_triggers(
            device_id=1,
            health_score=35.0,
            rul_days=20.0,
            recent_anomaly_count=0,
            existing_open_orders=[],
        )
        assert result is not None
        assert result["priority"] == "high"

    def test_medium_trigger(self):
        result = evaluate_triggers(
            device_id=1,
            health_score=55.0,
            rul_days=20.0,
            recent_anomaly_count=0,
            existing_open_orders=[],
        )
        assert result is not None
        assert result["priority"] == "medium"

    def test_no_trigger_healthy(self):
        result = evaluate_triggers(
            device_id=1,
            health_score=85.0,
            rul_days=60.0,
            recent_anomaly_count=1,
            existing_open_orders=[],
        )
        assert result is None

    def test_no_duplicate_same_priority(self):
        result = evaluate_triggers(
            device_id=1,
            health_score=15.0,
            rul_days=2.0,
            recent_anomaly_count=0,
            existing_open_orders=[
                {"priority": "critical", "status": "open"}
            ],
        )
        assert result is None

    def test_escalation(self):
        # Existing medium WO, but health dropped to critical
        result = evaluate_triggers(
            device_id=1,
            health_score=15.0,
            rul_days=2.0,
            recent_anomaly_count=0,
            existing_open_orders=[
                {"priority": "medium", "status": "open"}
            ],
        )
        assert result is not None
        assert result["priority"] == "critical"

    def test_anomaly_burst_trigger(self):
        result = evaluate_triggers(
            device_id=1,
            health_score=70.0,
            rul_days=30.0,
            recent_anomaly_count=6,
            existing_open_orders=[],
        )
        assert result is not None
        assert result["priority"] == "high"
        assert result["trigger_type"] == "anomaly_burst"

    def test_anomaly_burst_blocked_by_existing(self):
        result = evaluate_triggers(
            device_id=1,
            health_score=70.0,
            rul_days=30.0,
            recent_anomaly_count=6,
            existing_open_orders=[
                {"priority": "high", "status": "in_progress"}
            ],
        )
        assert result is None

    def test_rules_priority_order(self):
        # Rules should be ordered from most critical to least
        for i in range(len(RULES) - 1):
            assert (
                PRIORITY_RANK[RULES[i]["priority"]]
                > PRIORITY_RANK[RULES[i + 1]["priority"]]
            )

    def test_rul_none_no_crash(self):
        result = evaluate_triggers(
            device_id=1,
            health_score=15.0,
            rul_days=None,
            recent_anomaly_count=0,
            existing_open_orders=[],
        )
        assert result is not None
        assert result["priority"] == "critical"
