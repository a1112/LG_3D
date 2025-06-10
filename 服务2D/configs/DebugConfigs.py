import socket
from pathlib import Path


class DebugConfig:
    def __init__(self):
        self.hostname = socket.gethostname()
        if self.hostname == "DESKTOP-94ADH1G":
            self.FolderPath = Path(fr"G:\data\2025_06_06 15_34_04")
            self.save_folder = self.FolderPath.parent/"save"

    def get_surface_folder(self, surface_key):
        return self.FolderPath / surface_key
debug_config = DebugConfig()
