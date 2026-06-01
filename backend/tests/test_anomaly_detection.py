import numpy as np

from services.anomaly_detection import detect_three_sigma, detect_ewma, detect_anomalies


class TestThreeSigma:
    def test_detects_spike(self):
        rng = np.random.default_rng(42)
        readings = list(rng.normal(50, 2, 200))
        readings[150] = 70  # ~10-sigma spike
        anomalies = detect_three_sigma(readings, window_size=100)
        assert len(anomalies) > 0
        spike_indices = [a["index"] for a in anomalies]
        assert 150 in spike_indices

    def test_no_false_positive_on_normal_data(self):
        rng = np.random.default_rng(123)
        readings = list(rng.normal(50, 2, 500))
        anomalies = detect_three_sigma(readings, window_size=100)
        # With truly normal data, very few false positives expected (<1%)
        assert len(anomalies) < 5

    def test_severity_levels(self):
        # Use known sigma=5 by generating deterministic data
        rng = np.random.default_rng(7)
        readings = list(rng.normal(100, 5, 200))
        # Inject known spikes that will be measured against window sigma~5
        # After window of 100 samples, sigma should be ~5, mean ~100
        # z > 3 -> low, z > 4 -> medium, z > 5 -> high
        readings[150] = 118  # ~3.6 sigma -> low
        readings[170] = 122  # ~4.4 sigma -> medium
        readings[190] = 128  # ~5.6 sigma -> high
        anomalies = detect_three_sigma(readings, window_size=100)
        severities = {a["index"]: a["severity"] for a in anomalies}
        # At least verify severity ordering exists
        detected_at_150 = severities.get(150)
        detected_at_190 = severities.get(190)
        assert detected_at_150 is not None
        assert detected_at_190 is not None
        severity_order = {"low": 1, "medium": 2, "high": 3}
        assert severity_order[detected_at_190] >= severity_order[detected_at_150]

    def test_empty_window(self):
        readings = list(range(50))
        anomalies = detect_three_sigma(readings, window_size=100)
        assert anomalies == []


class TestEWMA:
    def test_detects_sudden_jump(self):
        rng = np.random.default_rng(55)
        readings = list(rng.normal(50, 1, 100))
        readings.append(65)  # sudden jump
        anomalies = detect_ewma(readings, span=30)
        assert len(anomalies) > 0
        assert any(a["index"] == 100 for a in anomalies)

    def test_detects_mean_shift(self):
        rng = np.random.default_rng(99)
        # 60 readings at mean=50, then shift to mean=60
        part1 = list(rng.normal(50, 1, 60))
        part2 = list(rng.normal(60, 1, 40))
        readings = part1 + part2
        anomalies = detect_ewma(readings, span=30, threshold_multiplier=3.0)
        # Should detect anomalies around the transition point
        assert len(anomalies) > 0
        transition_anomalies = [a for a in anomalies if 55 <= a["index"] <= 70]
        assert len(transition_anomalies) > 0

    def test_no_detection_on_stable(self):
        rng = np.random.default_rng(11)
        readings = list(rng.normal(50, 1, 200))
        anomalies = detect_ewma(readings, span=30)
        assert len(anomalies) < 3

    def test_short_series(self):
        anomalies = detect_ewma([1.0])
        assert anomalies == []


class TestCombined:
    def test_both_methods_run(self):
        rng = np.random.default_rng(77)
        readings = list(rng.normal(50, 2, 200))
        readings[150] = 80  # big spike
        anomalies = detect_anomalies(readings, window_size=100, ewma_span=30)
        methods = {a["method"] for a in anomalies}
        assert "three_sigma" in methods or "ewma" in methods
