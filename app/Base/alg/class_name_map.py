from typing import Any


def normalize_name_map(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(source): str(target) for source, target in value.items()}


def find_class_index(names: Any, target_name: str) -> int | None:
    if isinstance(names, dict):
        for index, name in names.items():
            if str(name) == target_name:
                return int(index)
        return None

    if isinstance(names, (list, tuple)):
        try:
            return list(names).index(target_name)
        except ValueError:
            return None

    return None


def mapped_class_result(pred_index: int,
                        pred_name: str,
                        names: Any,
                        name_map: dict[str, str]) -> tuple[int, str]:
    mapped_name = name_map.get(pred_name, pred_name)
    if mapped_name == pred_name:
        return pred_index, pred_name

    mapped_index = find_class_index(names, mapped_name)
    if mapped_index is None:
        return pred_index, mapped_name
    return mapped_index, mapped_name
