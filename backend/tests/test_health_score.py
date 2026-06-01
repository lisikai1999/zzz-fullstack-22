import numpy as np

from services.health_score import compute_sensor_score, compute_health_score, SENSOR_WEIGHTS


class TestSensorScore:
    def test_perfect_center(self):
        values = [60.0] * 50  # center of (40, 80) range
        score = compute_sensor_score(values, (40, 80))
        assert score > 90

    def test_at_boundary(self):
        values = [80.0] * 50  # at upper boundary
        score = compute_sensor_score(values, (40, 80))
        assert score < 20

    def test_out_of_range(self):
        values = [100.0] * 50  # well outside (40, 80)
        score = compute_sensor_score(values, (40, 80))
        assert score == 0.0

    def test_variance_penalty(self):
        stable = [60.0] * 50
        noisy = list(np.random.default_rng(1).normal(60, 8, 50))
        score_stable = compute_sensor_score(stable, (40, 80))
        score_noisy = compute_sensor_score(noisy, (40, 80))
        assert score_stable > score_noisy

    def test_trend_penalty(self):
        rising = [55 + i * 0.2 for i in range(50)]
        flat = [60.0] * 50
        score_rising = compute_sensor_score(rising, (40, 80))
        score_flat = compute_sensor_score(flat, (40, 80))
        assert score_flat > score_rising


class TestHealthScore:
    def test_perfect_health(self):
        sensor_data = {
            "temperature": [60.0] * 50,
            "vibration": [2.0] * 50,
            "current": [12.5] * 50,
        }
        result = compute_health_score("motor", sensor_data)
        assert result["health_score"] > 85

    def test_single_sensor_degraded(self):
        sensor_data = {
            "temperature": [75.0] * 50,  # near upper boundary
            "vibration": [1.9] * 50,  # center
            "current": [12.5] * 50,  # center
        }
        result = compute_health_score("motor", sensor_data)
        assert 40 < result["health_score"] < 90
        assert result["temperature_score"] < result["vibration_score"]

    def test_all_critical(self):
        sensor_data = {
            "temperature": [100.0] * 50,
            "vibration": [10.0] * 50,
            "current": [50.0] * 50,
        }
        result = compute_health_score("motor", sensor_data)
        assert result["health_score"] < 15

    def test_weight_distribution(self):
        # Vibration has weight 0.40, temperature 0.35, current 0.25
        assert SENSOR_WEIGHTS["vibration"] == 0.40
        assert SENSOR_WEIGHTS["temperature"] == 0.35
        assert SENSOR_WEIGHTS["current"] == 0.25
        assert abs(sum(SENSOR_WEIGHTS.values()) - 1.0) < 0.001

    def test_critical_minimum_penalty(self):
        sensor_data = {
            "temperature": [60.0] * 50,  # healthy
            "vibration": [60.0] * 50,  # way out of (0.3, 3.5) -> score ~0
            "current": [12.5] * 50,  # healthy
        }
        result = compute_health_score("motor", sensor_data)
        # The critical penalty should kick in (vibration score < 30)
        assert result["vibration_score"] < 10
        # Overall score should be lower due to critical penalty
        assert result["health_score"] < 60

    def test_missing_sensor(self):
        sensor_data = {
            "temperature": [60.0] * 50,
        }
        result = compute_health_score("motor", sensor_data)
        # Missing sensors default to 100
        assert result["vibration_score"] == 100.0
        assert result["current_score"] == 100.0
