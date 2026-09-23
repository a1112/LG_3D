from collections.abc import Mapping

from AlarmDetection.Result.GradResult import AlarmGradResult
from AlarmDetection.property import alarmConfigProperty
from Base.property.Base import DataIntegration
from Base.utils.Log import logger
from AlarmDetection.Result.errors import record_alarm_error


def _defect_config(data_integration):
    """Load the shared defect-class settings without making grading fragile."""
    try:
        from Base.CONFIG import defectClassesProperty

        return (getattr(defectClassesProperty, "data", {}) or {},
                bool((getattr(defectClassesProperty, "default", {}) or {}).get(
                    "show", True)), defectClassesProperty)
    except (AttributeError, ImportError, KeyError, TypeError, ValueError) as e:
        logger.warning("defect class config unavailable: %s", e)
    try:
        config = alarmConfigProperty.get_defect_config(data_integration)
        classes, default_show = config.get_config()
        return classes, default_show, config
    except (AttributeError, TypeError, ValueError, KeyError) as e:
        logger.warning("defect alarm config unavailable: %s", e)
        return {}, True, ""


def _iter_defects(defect_dict):
    if defect_dict is None:
        return
    if isinstance(defect_dict, Mapping):
        for name, entries in defect_dict.items():
            if isinstance(entries, (str, bytes)):
                entries = [entries]
            try:
                iterator = iter(entries)
            except TypeError:
                iterator = iter((entries,))
            for entry in iterator:
                yield str(name), entry
        return
    try:
        iterator = iter(defect_dict)
    except TypeError:
        iterator = iter((defect_dict,))
    for entry in iterator:
        name = getattr(entry, "defectName", None)
        if name is None and isinstance(entry, Mapping):
            name = entry.get("defectName", entry.get("name", ""))
        yield str(name or ""), entry


def grading_alarm_defects(data_integration: DataIntegration) -> AlarmGradResult:
    classes, default_show, config = _defect_config(data_integration)
    defect_dict = getattr(data_integration, "defect_dict", None)
    if defect_dict is None:
        record_alarm_error(data_integration, "defect", "缺陷检测未完成: 无有效检测结果")
        return AlarmGradResult(3, "缺陷检测未完成: 无有效检测结果", config)
    entries = list(_iter_defects(defect_dict) or ())
    shown = []
    for name, _entry in entries:
        class_config = classes.get(name, {}) if isinstance(classes, Mapping) else {}
        if not isinstance(class_config, Mapping):
            class_config = {}
        if not bool(class_config.get("show", default_show)):
            continue
        try:
            level = int(class_config.get("level", 1))
        except (TypeError, ValueError, OverflowError):
            level = 1
        shown.append((max(level, 1), name))
    if not shown:
        if entries:
            return AlarmGradResult(1, "缺陷均已屏蔽", config)
        return AlarmGradResult(1, "正常", config)
    max_level = max(level for level, _ in shown)
    names = sorted({name for level, name in shown if level == max_level and name})
    msg = f"检测到{len(shown)}个缺陷"
    if names:
        msg += f"：{'、'.join(names)}"
    return AlarmGradResult(max_level, msg, config)
