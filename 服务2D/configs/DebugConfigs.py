import socket
from pathlib import Path
import numpy as np
from PIL import Image

class DebugConfig:
    def __init__(self):
        self.hostname = socket.gethostname()
        if self.hostname == "DESKTOP-94ADH1G":
            self.FolderPath = Path(fr"G:\data\2025_06_06 15_34_04")
            self.save_folder = self.FolderPath.parent/"save"
            self.save_simple_folder = self.FolderPath.parent / "save_simple"

    def get_surface_folder(self, surface_key):
        return self.FolderPath / surface_key

    def save_simple_image(self,image, file_name):
        if not self.save_simple_folder.exists():
            self.save_simple_folder.mkdir(parents=True, exist_ok=True)
        if isinstance(image,np.ndarray):
            image = Image.fromarray(image)

        image.save(self.save_simple_folder / file_name)

debug_config = DebugConfig()
