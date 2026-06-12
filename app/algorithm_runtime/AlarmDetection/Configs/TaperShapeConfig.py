from .ConfigBase import ConfigBase
from Base.property.Base import DataIntegration


class TaperShapeConfigItem(ConfigBase):
    def __init__(self, config):
        super().__init__(config)
        self.config = config
        self.name = config.get("name", "默认判断规则")
        self.height = config.get("height", [60, 80])
        self.inner = config.get("inner", 0)
        self.outer = config.get("outer", 0)
        self.info = config.get("info", "")

    def get_config(self):
        return self.name, self.height, self.inner, self.outer, self.info


class TaperShapeConfig(ConfigBase):
    def __init__(self, config, data_integration: DataIntegration):
        super().__init__(config or {})
        self.data_integration = data_integration

    def _next_code(self):
        if hasattr(self.data_integration, "next_code"):
            return str(self.data_integration.next_code)
        return str(self.data_integration)

    def get_config(self):
        base_config = self.config.get("Base") or self.config.get("base") or {}
        item_config = self.config.get(self._next_code()) or {}
        config = dict(base_config)
        config.update(item_config)
        return TaperShapeConfigItem(config)
