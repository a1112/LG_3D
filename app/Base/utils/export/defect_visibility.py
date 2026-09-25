from CoilDataBase.models import CoilDefect

from Base import CONFIG

AREA_DEFECT_NAME_PREFIX = "2D_"


def _config_bool(value, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {
                "1", "true", "yes", "on", "show", "\u663e\u793a", "\u662f"
        }:
            return True
        if text in {
                "0", "false", "no", "off", "hide", "hidden", "\u5c4f\u853d",
                "\u5426"
        }:
            return False
    return bool(value)


def normalize_defect_name(defect_name: str) -> str:
    defect_name = str(defect_name or "")
    if defect_name.endswith(")") and "(" in defect_name:
        return defect_name.split("(")[0].rstrip()
    return defect_name


def shared_defect_name(defect_name: str) -> str:
    defect_name = normalize_defect_name(defect_name)
    if defect_name.upper().startswith(AREA_DEFECT_NAME_PREFIX):
        return defect_name[len(AREA_DEFECT_NAME_PREFIX):]
    return defect_name


def _format_config_name(defect_name: str) -> str:
    try:
        return CONFIG.defectClassesProperty.format_name(defect_name)
    except Exception:
        return defect_name


def _add_name_candidate(names: list[str], defect_name: str) -> None:
    if defect_name and defect_name not in names:
        names.append(defect_name)


def _add_name_variants(names: list[str], defect_name: str) -> None:
    normalized_name = normalize_defect_name(defect_name)
    _add_name_candidate(names, normalized_name)
    _add_name_candidate(names, _format_config_name(normalized_name))


def format_defect_name(defect_name: str) -> str:
    raw_name = str(defect_name or "")
    return _format_config_name(shared_defect_name(raw_name))


def defect_name_candidates(defect_or_name) -> list[str]:
    if isinstance(defect_or_name, str):
        values = [defect_or_name]
    else:
        values = [getattr(defect_or_name, "defectName", "")]

    names = []
    for value in values:
        raw_name = str(value or "")
        shared_name = shared_defect_name(raw_name)
        if shared_name != normalize_defect_name(raw_name):
            _add_name_variants(names, shared_name)
        _add_name_variants(names, raw_name)
    return names


def is_show_defect_class(defect_or_name) -> bool:
    try:
        default_show = _config_bool(
            CONFIG.defectClassesProperty.default.get("show", True), True)
        defect_config = CONFIG.defectClassesProperty.data
    except Exception:
        return True

    for defect_name in defect_name_candidates(defect_or_name):
        config = defect_config.get(defect_name)
        if config is not None:
            return _config_bool(config.get("show", default_show), default_show)
    return default_show


def _export_config_bool(export_config, key: str, default: bool) -> bool:
    if isinstance(export_config, dict):
        return _config_bool(export_config.get(key, default), default)
    return _config_bool(getattr(export_config, key, default), default)


def should_export_defect(defect: CoilDefect, export_config=None) -> bool:
    show_enabled = _export_config_bool(export_config, "defect_show_info", True)
    un_show_enabled = _export_config_bool(export_config, "defect_un_show_info",
                                          False)
    is_shown = is_show_defect_class(defect)
    return (is_shown and show_enabled) or (not is_shown and un_show_enabled)
