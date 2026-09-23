from collections.abc import Mapping

from Base.property.Base import DataIntegration
from .ConfigBase import ConfigBase


class DefectConfig(ConfigBase):
    # 缺陷 级别判断
    def __init__(self, config,data_integration:DataIntegration):
        super().__init__(config if isinstance(config, Mapping) else {})
        self.data_integration = data_integration

    def get_config(self):
        """Return the configured defect class map and its default visibility.

        Defect classes are normally managed by ``DefectClassesProperty`` and
        the alarm JSON may not contain a ``Defect`` section at all.  Keeping a
        small, explicit adapter here lets grading operate with either source
        without treating a missing section as an exception.
        """
        data = self.config.get("data", self.config.get("classes", self.config))
        if not isinstance(data, Mapping):
            data = {}
        default = self.config.get("default", {})
        if not isinstance(default, Mapping):
            default = {}
        return dict(data), bool(default.get("show", True))
