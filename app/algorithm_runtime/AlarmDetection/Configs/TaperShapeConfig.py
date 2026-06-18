import math

from .ConfigBase import ConfigBase
from Base.property.Base import DataIntegration


DEFAULT_TAPER_HEIGHT_LIMITS = [60, 80]


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
            int_text = str(int(numeric_value))
            if int_text not in candidates:
                candidates.append(int_text)

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
