import logging
import socket
from pathlib import Path
import json
import os

from Base.property.ControlConfigProperty import ControlConfigProperty
from Base.property.DefectClassesProperty import DefectClassesProperty
from Base.property.InfoConfigProperty import InfoConfigProperty
from Base.property.ServerConfigProperty import ServerConfigProperty

# parser = argparse.ArgumentParser()
# parser.add_argument('--config', type=str, default=None, help='3D服务配置文件')
# args = parser.parse_args()


# Log basic host info in ASCII to avoid encoding issues
is_local_host = socket.gethostname() in ["lcx_ace", "lcx_mov", "DESKTOP-94ADH1G", "MS-LGKRSZGOVODD", "DESKTOP-3VCH6DO"]
base_config_folder = Path(r"D:\CONFIG_3D")

try:
    file_url = Path(__file__)
    drive_config = Path(file_url.drive) / base_config_folder.relative_to(base_config_folder.drive)
    if drive_config.exists():
        base_config_folder = drive_config
except (NameError, ValueError):
    pass

offline_mode = (Path(base_config_folder) / "offline_mode=true").exists()

if offline_mode:
    from CoilDataBase.config import Config, DeriverList

    Config.deriver = DeriverList.sqlite
    Config.file_url = str(base_config_folder / "Coil.db")


def _env_flag(name: str) -> bool:
    value = os.getenv(name, "")
    return value.lower() in {"1", "true", "yes", "on"}


# 开发者模式：用于本地调试时强制使用 TestData 示例数据。
# 合并了原有的isLoc判断，统一为一个developer_mode设置
# 1. 通过环境变量 API_DEVELOPER_MODE=true 启用
# 2. 或在 CONFIG_3D 目录下放置文件 developer_mode=true
# 3. 或通过UI设置界面启用
# 4. 本地开发环境自动启用
developer_mode = (
    _env_flag("API_DEVELOPER_MODE") or 
    (Path(base_config_folder) / "developer_mode=true").exists() or
    is_local_host  # 本地开发环境自动启用
)

# 兼容性：保留isLoc变量以支持现有代码
isLoc = developer_mode

print(fr" app 运行模式 developer_mode：{developer_mode} is_local_host：{is_local_host}")
def get_file_url(base: str) -> Path:
    url = base_config_folder / base
    if not url.exists():
        logging.error("%s不存在！", url)
        return Path("../CONFIG_3D") / base
    return url


class JsonConfig:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.url = get_file_url(base_url)
        with self.url.open("r", encoding="utf-8") as f:
            self.config = json.load(f)


configFile = get_file_url("configs/Server3D.json")
alarmConfigFile = get_file_url(r"configs/Alarm.json")
infoConfigFile = get_file_url(r"configs/Info.json")
controlConfigFile = get_file_url(r"configs/Control.json")
defectClassesConfigFile = get_file_url(r"configs/DefectClasses.json")
DEBUG_MODEL = False


if isLoc:
    configFile = get_file_url(r"configs/Server3DLoc2.json")
    DEBUG_MODEL = True

# elif args.config:
#     configFile = Path(args.config)


def set_console_mode() -> None:
    import ctypes

    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-10), (0x4 | 0x80 | 0x20 | 0x2 | 0x10 | 0x1 | 0x00 | 0x100))


if not isLoc:
    set_console_mode()
data_base_api_port = 6011
server_api_port = 6010
image_api_port = 6012
serverConfigProperty = ServerConfigProperty(configFile)
infoConfigProperty = InfoConfigProperty(infoConfigFile)
defectClassesProperty = DefectClassesProperty(defectClassesConfigFile)
controlConfigProperty = ControlConfigProperty(controlConfigFile)

if socket.gethostname() == "DESKTOP-94ADH1G":
    serverConfigProperty.balsam_exe = r"C:\Qt\6.8.0\llvm-mingw_64\bin\balsam.exe"


def getAllKey():
    return "2D", "MASK", "3D"
