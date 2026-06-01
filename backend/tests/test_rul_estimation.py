import numpy as np

from services.rul_estimation import estimate_rul, FAILURE_THRESHOLD


class TestRulEstimation:
    def test_linear_degradation(self):
        # Health declining from 90 to 50 over 60 days
        history = [
            {"days_since_install": i * 7, "health_score": 90 - i * (40 / 9)}
            for i in range(10)
        ]
        result = estimate_rul(history)
        assert result["estimated_rul_days"] is not None
        assert result["fit_method"] in ("linear", "exponential")
        # With linear decline from 50 at day 63, threshold at 30
        # ~20 score points to go, declining ~4.4/week -> about 4.5 weeks = ~31 days
        assert 10 < result["estimated_rul_days"] < 80
        assert result["r_squared"] > 0.8

    def test_exponential_degradation(self):
        # Exponential decay pattern
        days = list(range(0, 91, 7))
        scores = [90 * np.exp(-0.008 * d) for d in days]
        history = [
            {"days_since_install": d, "health_score": s}
            for d, s in zip(days, scores)
        ]
        result = estimate_rul(history)
        assert result["estimated_rul_days"] is not None
        assert result["r_squared"] > 0.6

    def test_confidence_band(self):
        # Noisy linear degradation
        rng = np.random.default_rng(42)
        history = [
            {"days_since_install": i * 7, "health_score": 85 - i * 3 + rng.normal(0, 2)}
            for i in range(15)
        ]
        result = estimate_rul(history)
        if result["estimated_rul_days"] is not None:
            assert result["confidence_lower"] is not None
            assert result["confidence_upper"] is not None
            assert result["confidence_lower"] <= result["estimated_rul_days"]
            assert result["confidence_upper"] >= result["estimated_rul_days"]

    def test_insufficient_data(self):
        history = [
            {"days_since_install": 0, "health_score": 90},
            {"days_since_install": 7, "health_score": 88},
        ]
        result = estimate_rul(history)
        assert result["estimated_rul_days"] is None
        assert "error" in result

    def test_no_degradation_trend(self):
        # Flat or improving health
        history = [
            {"days_since_install": i * 7, "health_score": 85 + i * 0.5}
            for i in range(10)
        ]
        result = estimate_rul(history)
        assert result["estimated_rul_days"] is None

    def test_already_below_threshold(self):
        # Health already below failure threshold
        history = [
            {"days_since_install": i * 7, "health_score": 50 - i * 4}
            for i in range(10)
        ]
        # Last score: 50 - 36 = 14, below threshold
        result = estimate_rul(history)
        if result["estimated_rul_days"] is not None:
            assert result["estimated_rul_days"] <= 5

    def test_failure_threshold_value(self):
        assert FAILURE_THRESHOLD == 30.0
