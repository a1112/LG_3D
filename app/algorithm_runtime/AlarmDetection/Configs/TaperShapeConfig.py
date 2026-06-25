from collections.abc import Mapping
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
    if isinstance(values, Mapping):
        for value in values.values():
            yield from iter_taper_height_values(value)
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


def iter_taper_angle_values(values):
    if values is None:
        return
    if isinstance(values, Mapping):
        for value in values.values():
            yield from iter_taper_angle_values(value)
        return
    if isinstance(values, (list, tuple, set)):
        for value in values:
            yield from iter_taper_angle_values(value)
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
            .replace("|", ",")
        )
        if "," in normalized_text:
            for item in normalized_text.split(","):
                yield from iter_taper_angle_values(item)
            return
        numeric_tokens = _NUMBER_PATTERN.findall(normalized_text)
        if numeric_tokens and (
                len(numeric_tokens) > 1 or numeric_tokens[0] != normalized_text):
            for item in numeric_tokens:
                yield item
            return
        yield normalized_text
        return
    yield values


def normalize_taper_angles(values):
    angles = []
    for value in iter_taper_angle_values(values):
        try:
            angle = float(value)
        except (TypeError, ValueError, OverflowError):
            continue
        if math.isfinite(angle):
            normalized_angle = angle % 360.0
            if normalized_angle not in angles:
                angles.append(normalized_angle)
    return angles


class TaperShapeConfigItem(ConfigBase):
    def __init__(self, config):
        if not isinstance(config, Mapping):
            config = {}
        super().__init__(config)
        self.config = config
        self.name = config.get("name", "默认判断规则")
        self.height = config.get("height", DEFAULT_TAPER_HEIGHT_LIMITS)
        self.inner = config.get("inner", 0)
        self.outer = config.get("outer", 0)
        self.angles = (
            config.get("angles")
            if "angles" in config
            else config.get("angle", config.get("rotation_angles", config.get("rotation_angle")))
        )
        self.angle_tolerance = config.get("angle_tolerance", config.get("angleTolerance", 0))
        self.info = config.get("info", "")

    def get_config(self):
        return self.name, self.height, self.inner, self.outer, self.info


class TaperShapeConfig(ConfigBase):
    def __init__(self, config, data_integration: DataIntegration):
        if not isinstance(config, Mapping):
            config = {}
        super().__init__(config)
        self.data_integration = data_integration

    @staticmethod
    def _candidate_text(value) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            try:
                value = value.decode("utf-8")
            except UnicodeDecodeError:
                value = value.decode("utf-8", errors="ignore")

        return str(value).strip()

    @staticmethod
    def _append_unique_candidate(candidates: list[str], text: str) -> None:
        if text and text not in candidates:
            candidates.append(text)

    @staticmethod
    def _integer_candidate(text: str):
        try:
            numeric_value = float(text)
        except (TypeError, ValueError):
            return None
        if math.isfinite(numeric_value) and numeric_value.is_integer():
            return int(numeric_value)
        return None

    @staticmethod
    def _append_candidate(candidates: list[str], value) -> None:
        text = TaperShapeConfig._candidate_text(value)
        TaperShapeConfig._append_unique_candidate(candidates, text)

        int_value = TaperShapeConfig._integer_candidate(text)
        if int_value is None:
            return

        TaperShapeConfig._append_unique_candidate(candidates, str(int_value))
        if 32 <= int_value <= 126:
            TaperShapeConfig._append_unique_candidate(candidates,
                                                     chr(int_value))

    @staticmethod
    def _append_candidates(candidates: list[str], values) -> None:
        texts = []
        for value in values:
            text = TaperShapeConfig._candidate_text(value)
            if text:
                texts.append(text)
                TaperShapeConfig._append_unique_candidate(candidates, text)

        for text in texts:
            int_value = TaperShapeConfig._integer_candidate(text)
            if int_value is not None:
                TaperShapeConfig._append_unique_candidate(
                    candidates, str(int_value))

        for text in texts:
            int_value = TaperShapeConfig._integer_candidate(text)
            if int_value is not None and 32 <= int_value <= 126:
                TaperShapeConfig._append_unique_candidate(
                    candidates, chr(int_value))

    @staticmethod
    def _append_attr_candidate_value(values: list, source, attr: str) -> None:
        try:
            value = getattr(source, attr)
        except (AttributeError, TypeError, ValueError, OverflowError):
            return
        if value is not None:
            values.append(value)

    @staticmethod
    def _append_mapping_candidate_value(values: list, source, key: str) -> None:
        try:
            value = source.get(key)
        except (AttributeError, TypeError, ValueError):
            return
        if value is not None:
            values.append(value)

    def _next_code_candidate_values(self):
        source = self.data_integration
        values = []
        alias_values = []

        self._append_attr_candidate_value(values, source, "next_code")
        for attr in ("nextCode", "NextCode", "next_code_value",
                     "NextCodeValue"):
            self._append_attr_candidate_value(alias_values, source, attr)

        if isinstance(source, Mapping):
            for key in ("next_code", "nextCode", "NextCode",
                        "next_code_value", "NextCodeValue"):
                self._append_mapping_candidate_value(alias_values, source, key)

        # Legacy integrations may return integer 49 when the source coil is
        # unavailable. Keep real aliases ahead of that failure sentinel so the
        # alarm rule does not accidentally fall back to code "1".
        if values == [49] and alias_values:
            values = alias_values + values
        else:
            values.extend(alias_values)

        if not values:
            values.append(source)
        return values

    def _next_code_candidates(self):
        candidates = []
        self._append_candidates(candidates, self._next_code_candidate_values())
        return candidates

    def _get_item_config(self):
        for next_code in self._next_code_candidates():
            item_config = self.config.get(next_code)
            if isinstance(item_config, Mapping) and item_config:
                return item_config
        return {}

    def get_config(self):
        base_config = self.config.get("Base") or self.config.get("base") or {}
        if not isinstance(base_config, Mapping):
            base_config = {}
        item_config = self._get_item_config()
        config = dict(base_config)
        config.update(item_config)
        return TaperShapeConfigItem(config)
