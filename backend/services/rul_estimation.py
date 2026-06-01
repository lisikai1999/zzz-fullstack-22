import numpy as np
from scipy.optimize import curve_fit
from scipy.stats import t as t_dist

FAILURE_THRESHOLD = 30.0


def _linear_model(x, a, b):
    return a * x + b


def _exponential_model(x, a, b, c):
    return a * np.exp(b * x) + c


def estimate_rul(
    health_history: list[dict], failure_threshold: float = FAILURE_THRESHOLD
) -> dict:
    if len(health_history) < 5:
        return {
            "estimated_rul_days": None,
            "fit_method": "none",
            "r_squared": 0.0,
            "confidence_lower": None,
            "confidence_upper": None,
            "failure_threshold": failure_threshold,
            "error": "Insufficient data",
        }

    times = np.array([h["days_since_install"] for h in health_history], dtype=float)
    scores = np.array([h["health_score"] for h in health_history], dtype=float)

    t_offset = times[0]
    t_norm = times - t_offset
    t_current = t_norm[-1]

    result = {"failure_threshold": failure_threshold}

    # Try exponential fit
    try:
        popt_exp, _ = curve_fit(
            _exponential_model,
            t_norm,
            scores,
            p0=[scores[0], -0.005, 0],
            maxfev=5000,
            bounds=([-np.inf, -1, -np.inf], [np.inf, 0, np.inf]),
        )
        predicted_exp = _exponential_model(t_norm, *popt_exp)
        ss_res = np.sum((scores - predicted_exp) ** 2)
        ss_tot = np.sum((scores - np.mean(scores)) ** 2)
        r_squared_exp = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        if r_squared_exp > 0.6 and popt_exp[1] < 0:
            a, b, c = popt_exp
            target = failure_threshold - c
            if target > 0 and a > 0:
                t_fail = np.log(target / a) / b
                rul = t_fail - t_current
                if rul > 0:
                    n = len(scores)
                    residual_std = np.sqrt(ss_res / (n - 3))
                    health_slope = a * b * np.exp(b * t_current)
                    time_std = (
                        residual_std / abs(health_slope)
                        if health_slope != 0
                        else rul * 0.3
                    )
                    t_crit = t_dist.ppf(0.975, n - 3)

                    result.update(
                        {
                            "estimated_rul_days": round(float(rul), 1),
                            "fit_method": "exponential",
                            "r_squared": round(float(r_squared_exp), 4),
                            "confidence_lower": round(
                                float(max(0, rul - t_crit * time_std)), 1
                            ),
                            "confidence_upper": round(
                                float(rul + t_crit * time_std), 1
                            ),
                        }
                    )
                    return result
    except (RuntimeError, ValueError, TypeError):
        pass

    # Linear fit fallback
    coeffs = np.polyfit(t_norm, scores, 1)
    slope, intercept = coeffs

    if slope >= 0:
        result.update(
            {
                "estimated_rul_days": None,
                "fit_method": "linear",
                "r_squared": 0.0,
                "confidence_lower": None,
                "confidence_upper": None,
                "error": "No degradation trend",
            }
        )
        return result

    predicted_lin = np.polyval(coeffs, t_norm)
    ss_res = np.sum((scores - predicted_lin) ** 2)
    ss_tot = np.sum((scores - np.mean(scores)) ** 2)
    r_squared_lin = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    t_fail = (failure_threshold - intercept) / slope
    rul = max(0.0, t_fail - t_current)

    n = len(scores)
    residual_std = np.sqrt(ss_res / (n - 2)) if n > 2 else 0
    time_std = residual_std / abs(slope) if slope != 0 else 0
    t_crit = t_dist.ppf(0.975, max(1, n - 2))

    result.update(
        {
            "estimated_rul_days": round(float(rul), 1),
            "fit_method": "linear",
            "r_squared": round(float(r_squared_lin), 4),
            "confidence_lower": round(float(max(0, rul - t_crit * time_std)), 1),
            "confidence_upper": round(float(rul + t_crit * time_std), 1),
        }
    )
    return result


def generate_prediction_curve(
    health_history: list[dict], failure_threshold: float = FAILURE_THRESHOLD
) -> dict:
    if len(health_history) < 5:
        return {
            "historical": [],
            "predicted": [],
            "confidence_upper": [],
            "confidence_lower": [],
            "failure_threshold": failure_threshold,
        }

    times = np.array([h["days_since_install"] for h in health_history], dtype=float)
    scores = np.array([h["health_score"] for h in health_history], dtype=float)

    t_offset = times[0]
    t_norm = times - t_offset
    t_current = t_norm[-1]

    historical = [
        {"day": float(times[i]), "score": float(scores[i])}
        for i in range(len(times))
    ]

    # Fit and predict forward
    coeffs = np.polyfit(t_norm, scores, 1)
    slope, intercept = coeffs

    if slope >= 0:
        return {
            "historical": historical,
            "predicted": [],
            "confidence_upper": [],
            "confidence_lower": [],
            "failure_threshold": failure_threshold,
        }

    future_days = int(min(365, (failure_threshold - intercept) / slope - t_current + 30))
    future_days = max(30, future_days)

    t_future = np.linspace(t_current, t_current + future_days, 50)
    predicted_scores = np.polyval(coeffs, t_future)

    n = len(scores)
    ss_res = np.sum((scores - np.polyval(coeffs, t_norm)) ** 2)
    residual_std = np.sqrt(ss_res / (n - 2)) if n > 2 else 0
    t_crit = t_dist.ppf(0.975, max(1, n - 2))

    predicted = [
        {"day": float(t_future[i] + t_offset), "score": float(predicted_scores[i])}
        for i in range(len(t_future))
    ]
    conf_upper = [
        {
            "day": float(t_future[i] + t_offset),
            "score": float(predicted_scores[i] + t_crit * residual_std),
        }
        for i in range(len(t_future))
    ]
    conf_lower = [
        {
            "day": float(t_future[i] + t_offset),
            "score": float(max(0, predicted_scores[i] - t_crit * residual_std)),
        }
        for i in range(len(t_future))
    ]

    return {
        "historical": historical,
        "predicted": predicted,
        "confidence_upper": conf_upper,
        "confidence_lower": conf_lower,
        "failure_threshold": failure_threshold,
    }
