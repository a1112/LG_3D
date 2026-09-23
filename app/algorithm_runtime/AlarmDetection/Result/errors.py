"""Processing failures are distinct from a successfully measured product alarm."""


def record_alarm_error(data_integration, stage: str, error) -> None:
    message = f"{stage}: {error}"
    errors = getattr(data_integration, "alarm_processing_errors", None)
    if errors is None:
        errors = []
        data_integration.alarm_processing_errors = errors
    if message not in errors:
        errors.append(message)


def alarm_error_result(data_integration) -> dict[str, list[str]]:
    errors = getattr(data_integration, "alarm_processing_errors", None) or []
    if not errors:
        return {}
    surface = str(getattr(data_integration, "key", None)
                  or getattr(data_integration, "surface", "unknown"))
    return {surface: list(errors)}


def merge_alarm_errors(target: dict, result) -> None:
    if not isinstance(result, dict):
        return
    for surface, messages in result.items():
        surface_errors = target.setdefault(surface, [])
        for message in messages:
            if message not in surface_errors:
                surface_errors.append(message)
