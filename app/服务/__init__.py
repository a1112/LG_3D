"""
BKVision service package.

Adds the shared Base directory to sys.path so property/utils/CONFIG imports
resolve to the centralized implementation.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1] / "Base"
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
