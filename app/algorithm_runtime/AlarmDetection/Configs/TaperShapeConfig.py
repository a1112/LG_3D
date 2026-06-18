import math
import re

from .ConfigBase import ConfigBase
from Base.property.Base import DataIntegration


DEFAULT_TAPER_HEIGHT_LIMITS = [60, 80]
_NUMBER_PATTERN = re.compile(
    r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
)


def iter_taper_height_values(values):
    if values is None:
        return
    if isinstance(values, (list, tuple, set)):
        for value in values:
            yield from iter_taper_height_values(value)
        return
    if isinstance(values, str):
        text = values.strip()
        if not text:
            return
        if len(text) >= 2 and text[0] in "[(" and text[-1] in "])":
            text = text[1:-1].strip()
        normalized_text = (
            text
            .replace("，", ",")
            .replace("；", ",")
            .replace(";", ",")
        )
        if "," in normalized_text:
            for item in normalized_text.split(","):
                yield from iter_taper_height_values(item)
            return
        numeric_tokens = _NUMBER_PATTERN.findall(normalized_text)
        if numeric_tokens and (
                len(numeric_tokens) > 1 or numeric_tokens[0] != normalized_text):
            for item in numeric_tokens:
                yield item
            return
        yield text
        return
    yield values


def normalize_taper_height_limits(values,
                                  default_limits=DEFAULT_TAPER_HEIGHT_LIMITS):
    limits = []
    for value in iter_taper_height_values(values):
        try:
            limit = abs(float(value))
        except (TypeError, ValueError, OverflowError):
            continue
        if math.isfinite(limit) and limit > 0:
            limits.append(limit)
    if limits:
        return sorted(limits)

    default_values = []
    for value in iter_taper_height_values(default_limits):
        try:
            limit = abs(float(value))
        except (TypeError, ValueError, OverflowError):
            continue
        if math.isfinite(limit) and limit > 0:
            default_values.append(limit)
    return sorted(default_values)


class TaperShapeConfigItem(ConfigBase):
    def __init__(self, config):
        super().__init__(config)
        self.config = config
        self.name = config.get("name", "默认判断规则")
        self.height = config.get("height", DEFAULT_TAPER_HEIGHT_LIMITS)
        self.inner = config.get("inner", 0)
        self.outer = config.get("outer", 0)
        self.info = config.get("info", "")

    def get_config(self):
        return self.name, self.height, self.inner, self.outer, self.info


class TaperShapeConfig(ConfigBase):
    def __init__(self, config, data_integration: DataIntegration):
        super().__init__(config or {})
        self.data_integration = data_integration

    @staticmethod
    def _append_candidate(candidates: list[str], value) -> None:
        if value is None:
            return
        if isinstance(value, bytes):
            try:
                value = value.decode("utf-8")
            except UnicodeDecodeError:
                value = value.decode("utf-8", errors="ignore")

        text = str(value).strip()
        if text and text not in candidates:
            candidates.append(text)

        try:
            numeric_value = float(text)
        except (TypeError, ValueError):
            return
        if math.isfinite(numeric_value) and numeric_value.is_integer():
            int_value = int(numeric_value)
            int_text = str(int_value)
            if int_text not in candidates:
                candidates.append(int_text)
            if 32 <= int_value <= 126:
                ascii_text = chr(int_value)
                if ascii_text and ascii_text not in candidates:
                    candidates.append(ascii_text)

    def _next_code_candidates(self):
        candidates = []
        if hasattr(self.data_integration, "next_code"):
            self._append_candidate(candidates, self.data_integration.next_code)
        else:
            self._append_candidate(candidates, self.data_integration)
        return candidates

    def _get_item_config(self):
        for next_code in self._next_code_candidates():
            item_config = self.config.get(next_code)
            if item_config:
                return item_config
        return {}

    def get_config(self):
        base_config = self.config.get("Base") or self.config.get("base") or {}
        item_config = self._get_item_config()
        config = dict(base_config)
        config.update(item_config)
        return TaperShapeConfigItem(config)
