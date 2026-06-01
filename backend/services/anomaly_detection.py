import math

import numpy as np


def detect_three_sigma(
    readings: list[float], window_size: int = 100
) -> list[dict]:
    anomalies = []
    if len(readings) <= window_size:
        return anomalies

    for i in range(window_size, len(readings)):
        window = readings[i - window_size : i]
        mu = np.mean(window)
        sigma = np.std(window)
        if sigma == 0:
            continue
        z_score = abs(readings[i] - mu) / sigma
        if z_score > 3.0:
            severity = "high" if z_score > 5 else "medium" if z_score > 4 else "low"
            anomalies.append(
                {
                    "index": i,
                    "value": readings[i],
                    "threshold": mu + 3 * sigma * (1 if readings[i] > mu else -1),
                    "z_score": round(z_score, 2),
                    "severity": severity,
                    "method": "three_sigma",
                }
            )
    return anomalies


def detect_ewma(
    readings: list[float], span: int = 30, threshold_multiplier: float = 3.0
) -> list[dict]:
    if len(readings) < 2:
        return []

    alpha = 2.0 / (span + 1)
    anomalies = []
    ewma = readings[0]
    ewma_var = 0.0

    for i in range(1, len(readings)):
        residual = readings[i] - ewma
        ewma = alpha * readings[i] + (1 - alpha) * ewma
        ewma_var = alpha * residual**2 + (1 - alpha) * ewma_var
        ewma_std = math.sqrt(ewma_var) if ewma_var > 0 else 0

        if i < span:
            continue

        if ewma_std > 0 and abs(residual) > threshold_multiplier * ewma_std:
            deviation_factor = abs(residual) / ewma_std
            severity = (
                "high" if deviation_factor > 5 else "medium" if deviation_factor > 4 else "low"
            )
            anomalies.append(
                {
                    "index": i,
                    "value": readings[i],
                    "ewma": round(ewma, 4),
                    "threshold": round(threshold_multiplier * ewma_std, 4),
                    "severity": severity,
                    "method": "ewma",
                }
            )
    return anomalies


def detect_anomalies(
    readings: list[float], window_size: int = 100, ewma_span: int = 30
) -> list[dict]:
    sigma_results = detect_three_sigma(readings, window_size)
    ewma_results = detect_ewma(readings, ewma_span)

    all_anomalies = sigma_results + ewma_results
    all_anomalies.sort(key=lambda x: x["index"])
    return all_anomalies
