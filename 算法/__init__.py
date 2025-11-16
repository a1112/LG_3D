"""
Algorithm background runtime package.

Exposes BackgroundRuntime and runtime_controller for services that need the
long-running algorithm loop.
"""

from .runtime import BackgroundRuntime, runtime_controller

__all__ = ["BackgroundRuntime", "runtime_controller"]
