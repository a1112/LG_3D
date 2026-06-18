import math

from AlarmDetection.Configs.TaperShapeConfig import (
    DEFAULT_TAPER_HEIGHT_LIMITS,
    iter_taper_height_values,
)


def _positive_finite(value):
    try:
        limit = abs(float(value))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(limit) or limit <= 0:
        return None
    return limit


def taper_error_threshold_from_limits(height_limits,
                                      default_threshold: float | None = None
                                      ) -> tuple[float, float]:
    limits = []
    for value in iter_taper_height_values(height_limits):
        limit = _positive_finite(value)
        if limit is not None:
            limits.append(limit)

    if not limits:
        threshold = _positive_finite(default_threshold)
        if threshold is None:
            threshold = float(min(DEFAULT_TAPER_HEIGHT_LIMITS))
        return threshold, threshold

    threshold = min(limits)
    return threshold, threshold
