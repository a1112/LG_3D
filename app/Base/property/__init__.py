"""
Redirect property package to shared Base/property implementation.
"""
from pathlib import Path

# Point this package to the central Base/property folder to keep 服务与算法共用一套定义
__path__ = [str(Path(__file__).resolve().parents[2] / "Base" / "property")]

