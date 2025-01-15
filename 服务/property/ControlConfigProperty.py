from pathlib import Path

from property.BaseConfigProperty import BaseConfigProperty


class ControlConfigProperty(BaseConfigProperty):
    def __init__(self, file_path: Path):
        super().__init__(file_path)