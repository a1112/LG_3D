import json
from abc import ABC
from pathlib import Path


class BaseConfigProperty(ABC):
    def __init__(self, file_path:Path):
        self.file_path = file_path
        self.encoding="utf-8"
        self.config=self.load_config()

    def load_config(self):
        """
        加载配置文件
        :return: dict
        """
        return json.load(open(self.file_path, 'r', encoding=self.encoding))

    def save_config(self):
        """
        保存配置文件
        :return:None
        """
        json.dump(self.config, open(self.file_path, 'w', encoding=self.encoding),indent=4,ensure_ascii=False)
