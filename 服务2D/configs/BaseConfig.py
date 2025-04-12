import json
from pathlib import Path,WindowsPath

class BaseConfig:
    def __init__(self,f_):
        if isinstance(f_,(str,WindowsPath)):
            self.config = json.load(open(f_, "r", encoding = "utf-8"))
        else:
            self.config = f_

    def get_value(self,key,default):
        try:
            return self.config[key]
        except KeyError:
            return default