from collections.abc import Mapping

from .ConfigBase import ConfigBase
from Base.property.Base import DataIntegration

class FlatRollConfigItem(ConfigBase):
    def __init__(self, config):
        if not isinstance(config, Mapping):
            config = {}
        super().__init__(config)
        self.name = config.get("name", "默认判断规则")
        self.filter = config.get("filter", {})
        self.max = config.get("max", 780)
        self.min = config.get("min", 600)
        self.msg = config.get("msg", config.get("info", ""))

    def get_config(self):
        return self.name, self.max, self.min, self.msg

class FlatRollConfig(ConfigBase):
    """
    按去向选择扁卷内径判断规则。
    """
    def __init__(self, config,data_integration:DataIntegration):
        if not isinstance(config, Mapping):
            config = {}
        super().__init__(config)
        self.data_integration = data_integration

    def get_config(self):
        base = self.config.get("Base", self.config.get("base", {}))
        if not isinstance(base, Mapping):
            base = {}
        code = getattr(self.data_integration, "next_code", None)
        candidates = [str(code)] if code is not None else []
        try:
            number = int(float(code))
            candidates.extend((str(number), chr(number)))
        except (TypeError, ValueError, OverflowError):
            pass
        selected = {}
        for candidate in candidates:
            item = self.config.get(candidate)
            if isinstance(item, Mapping):
                selected = item
                break
        merged = dict(base)
        merged.update(selected)
        return FlatRollConfigItem(merged)
