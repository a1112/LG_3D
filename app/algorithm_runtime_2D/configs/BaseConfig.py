import json
from os import PathLike


class BaseConfig:
    def __init__(self, f_):
        self._run_ = True
        if isinstance(f_, (str, PathLike)):
            with open(f_, "r", encoding="utf-8") as config_file:
                self.config = json.load(config_file)
        else:
            self.config = f_

    def get_value(self, key, default):
        try:
            return self.config[key]
        except KeyError:
            return default
