import os
from pathlib import Path

log_folder=Path("logs")

disk_monitor_log_dir = log_folder/"DiskMonitor"
disk_monitor_log_dir.mkdir(parents=True, exist_ok=True)

config_folder = Path("config")

disk_monitor_config=config_folder/"DiskMonitor.json"