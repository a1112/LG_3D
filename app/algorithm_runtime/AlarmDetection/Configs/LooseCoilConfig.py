from collections.abc import Mapping

from .ConfigBase import ConfigBase
from Base.property.Base import DataIntegration

class LooseCoilConfigItem(ConfigBase):
    def __init__(self, config):
        if not isinstance(config, Mapping):
            config = {}
        super().__init__(config)
        self.config = config
        self.name = config.get("name", "默认判断规则")
        self.width = config.get("width", 25)
        self.info = config.get("info", config.get("msg", ""))

        self.camera_map = {}

    def get_config(self):
        return self.name, self.width, self.info

class LooseCoilConfig(ConfigBase):
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
        return LooseCoilConfigItem(merged)
