from AlarmDetection.Configs.TaperShapeConfig import DEFAULT_TAPER_HEIGHT_LIMITS


def taper_error_threshold_from_limits(height_limits,
                                      default_threshold: float | None = None
                                      ) -> tuple[float, float]:
    if not isinstance(height_limits, (list, tuple)):
        height_limits = [height_limits]

    limits = []
    for value in height_limits:
        try:
            limit = abs(float(value))
        except (TypeError, ValueError):
            continue
        if limit > 0:
            limits.append(limit)

    if not limits:
        if default_threshold is None:
            threshold = float(min(DEFAULT_TAPER_HEIGHT_LIMITS))
        else:
            threshold = float(default_threshold)
        return threshold, threshold

    threshold = min(limits)
    return threshold, threshold
