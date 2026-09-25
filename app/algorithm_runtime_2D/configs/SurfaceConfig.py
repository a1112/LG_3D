
import os
import time
from pathlib import Path

from . import CONFIG
from .BaseConfig import BaseConfig
from .CameraConfig import CameraConfig
from .DebugConfigs import debug_config
from .GlobJoinConfig import GlobalJoinConfigS, GlobalJoinConfigL


class SurfaceConfig(BaseConfig):
    def __init__(self,surface_key, f_):
        self.surface_key = surface_key
        super().__init__(f_)

        self.global_config = GlobalJoinConfigL() if self.surface_key=="L" else GlobalJoinConfigS()
        self.image_size = 5120

        self.camera_configs = [CameraConfig(surface_key,c,self) for c in self.config["cameras"] ]
        clip_config = self.get_value("clip_config", {})
        default_clip_c = 2600 if self.surface_key == "S" else 4000
        self.clip_mode = clip_config.get("mode", "fixed")
        self.clip_fixed = int(clip_config.get("fixed", 200))
        self.clip_dynamic_a = float(clip_config.get("a", 3))
        self.clip_dynamic_b = float(clip_config.get("b", 220))
        self.clip_dynamic_c = float(clip_config.get("c", default_clip_c))
        self.clip_dynamic_offset = int(clip_config.get("offset", 40))
        if CONFIG.DEBUG:
            self.image_size = 1024
            self.save_folder= debug_config.save_folder/surface_key
        else:
            self.save_folder = self.config["save_folder"]

        self.scale = self.image_size / 512

        self.area_copy_to_folder = CONFIG.base_debug_image_save_folder/"area_copy_to_folder"/self.surface_key

    def is_run(self):
        return self._run_

    def get_source_snapshot(self, coil_id):
        snapshot = []
        for camera_config in self.camera_configs:
            folder = camera_config.get_folder(coil_id)
            files = []
            try:
                with os.scandir(folder) as entries:
                    for entry in entries:
                        if not entry.is_file() or not entry.name.lower().endswith(".jpg"):
                            continue
                        stat = entry.stat()
                        files.append((entry.name, stat.st_size, stat.st_mtime_ns))
            except (FileNotFoundError, OSError):
                files = []
            snapshot.append((camera_config.key, tuple(sorted(files))))
        return tuple(snapshot)

    @staticmethod
    def source_snapshot_complete(
            snapshot,
            *,
            min_images_per_camera: int = 2,
            max_camera_count_skew: int = 2,
            quiet_seconds: float = 0.0,
    ) -> bool:
        counts = [len(files) for _, files in snapshot]
        if not counts or any(count < min_images_per_camera for count in counts):
            return False
        if any(size <= 0 for _, files in snapshot for _, size, _ in files):
            return False
        if max(counts) - min(counts) > max_camera_count_skew:
            return False
        if quiet_seconds <= 0:
            return True

        latest_mtime_ns = max(
            (mtime_ns for _, files in snapshot for _, _, mtime_ns in files),
            default=0,
        )
        return latest_mtime_ns > 0 and time.time_ns() - latest_mtime_ns >= int(quiet_seconds * 1_000_000_000)

    def source_complete(
            self,
            coil_id,
            *,
            min_images_per_camera: int = 2,
            max_camera_count_skew: int = 2,
            quiet_seconds: float = 0.0,
    ) -> bool:
        return self.source_snapshot_complete(
            self.get_source_snapshot(coil_id),
            min_images_per_camera=min_images_per_camera,
            max_camera_count_skew=max_camera_count_skew,
            quiet_seconds=quiet_seconds,
        )

    def get_area_url_base(self, coil_id, type_, name="AREA"):
        base_folder = Path(self.save_folder)/str(coil_id)
        if CONFIG.DEBUG:
            base_folder.mkdir(parents=True, exist_ok=True)

        return base_folder/type_/f"{name}.jpg"

    def get_area_url(self, coil_id, name="AREA"):
        return self.get_area_url_base(coil_id, "jpg", name)

    def get_area_url_pre(self, coil_id, name="AREA"):
        return self.get_area_url_base(coil_id, "preview", name)

    def get_area_completion_marker(self, coil_id) -> Path:
        return Path(self.save_folder) / str(coil_id) / ".area_complete"

    def get_area_in_progress_marker(self, coil_id) -> Path:
        return Path(self.save_folder) / str(coil_id) / ".area_in_progress"

    def area_output_complete(self, coil_id) -> bool:
        area_exists = self.get_area_url(coil_id).exists()
        if self.get_area_completion_marker(coil_id).exists():
            return area_exists
        if self.get_area_in_progress_marker(coil_id).exists():
            return False
        # Outputs created before completion markers were introduced remain valid.
        return area_exists
