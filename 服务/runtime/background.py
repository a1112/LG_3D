"""
Backward-compatible shim for the background runtime that now lives in 算法/.
"""

from 算法.runtime import BackgroundRuntime, runtime_controller  # noqa: F401

__all__ = ["BackgroundRuntime", "runtime_controller"]
