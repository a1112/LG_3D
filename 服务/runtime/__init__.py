"""
Runtime helpers for coordinating background services that need to live
alongside the FastAPI application.
"""

from 算法.runtime import BackgroundRuntime, runtime_controller

__all__ = ["BackgroundRuntime", "runtime_controller"]
