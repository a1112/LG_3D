def taper_error_threshold_from_limits(height_limits,
                                      default_threshold: float = 100
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
        threshold = float(default_threshold)
        return threshold, threshold

    threshold = min(limits)
    return threshold, threshold
