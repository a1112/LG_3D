"""
Shim package to maintain backward compatibility after relocating the algorithm
runtime to the repository root.
"""

from 算法.runtime import BackgroundRuntime, runtime_controller

__all__ = ["BackgroundRuntime", "runtime_controller"]
