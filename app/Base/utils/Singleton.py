"""
服务单例运行锁模块 - 防止服务重复启动

提供两种防重复启动机制：
1. PID 文件锁 - 基于文件系统锁
2. 端口占用检测 - 基于端口是否已监听

使用方式：
    # 方式1: 装饰器
    @singleton("my_service", port=8080)
    def main():
        ...

    # 方式2: 上下文管理器
    with SingletonLock("my_service", port=8080):
        ...
"""
from __future__ import annotations

import ctypes
import logging
import os
import socket
import sys
import threading
from contextlib import contextmanager
from functools import wraps
from pathlib import Path

# Unix 特定模块，仅在需要时导入
if sys.platform != "win32":
    import fcntl

logger = logging.getLogger(__name__)

# Windows 平台使用 mutex，Unix 使用文件锁
if sys.platform == "win32":
    _kernel32 = ctypes.windll.kernel32

    class _WindowsLock:
        """Windows 互斥锁"""

        def __init__(self, name: str):
            self.name = name
            self.handle = None

        def acquire(self) -> bool:
            # 创建全局命名的互斥锁
            self.handle = _kernel32.CreateMutexW(None, False, f"Global\\{self.name}")
            if not self.handle:
                return False
            # 检查是否已存在
            if _kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
                _kernel32.CloseHandle(self.handle)
                self.handle = None
                return False
            return True

        def release(self) -> None:
            if self.handle:
                _kernel32.CloseHandle(self.handle)
                self.handle = None

else:
    _WindowsLock = None  # type: ignore


class _FileLock:
    """Unix 文件锁"""

    def __init__(self, path: Path):
        self.path = path
        self.fd = None

    def acquire(self) -> bool:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.fd = open(self.path, "w")
            fcntl.lockf(self.fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.fd.write(str(os.getpid()))
            self.fd.flush()
            return True
        except (IOError, OSError):
            if self.fd:
                try:
                    self.fd.close()
                except Exception:
                    pass
                self.fd = None
            return False

    def release(self) -> None:
        if self.fd:
            try:
                fcntl.lockf(self.fd.fileno(), fcntl.LOCK_UN)
                self.fd.close()
            except Exception:
                pass
            try:
                self.path.unlink(missing_ok=True)
            except Exception:
                pass
            self.fd = None


class SingletonLock:
    """
    单例锁 - 防止服务重复启动

    参数:
        name: 服务名称，用于生成锁文件名
        pid_dir: PID 文件目录，默认为 ./pids
        port: 可选，检查端口是否被占用
        host: 端口检查的主机，默认为 127.0.0.1
        auto_cleanup: 进程退出时自动清理锁文件
    """

    def __init__(
        self,
        name: str,
        pid_dir: Path | str | None = None,
        port: int | None = None,
        host: str = "127.0.0.1",
        auto_cleanup: bool = True,
    ):
        self.name = name
        self.port = port
        self.host = host
        self.auto_cleanup = auto_cleanup
        self._locked = False
        self._cleanup_registered = False

        # 确定 PID 目录
        if pid_dir is None:
            # 默认使用项目根目录下的 pids 目录
            project_root = Path(__file__).resolve().parents[3]
            pid_dir = project_root / "pids"
        self.pid_dir = Path(pid_dir)
        self.pid_file = self.pid_dir / f"{name}.pid"

        # 创建锁对象
        if sys.platform == "win32":
            self._lock_impl = _WindowsLock(f"LG_3D_{name}")
        else:
            self._lock_impl = _FileLock(self.pid_file)

    def _check_port_available(self) -> bool:
        """检查端口是否可用"""
        if self.port is None:
            return True
        try:
            with socket.create_connection((self.host, self.port), timeout=0.5):
                return False  # 端口已被占用
        except OSError:
            return True  # 端口可用

    def _read_existing_pid(self) -> int | None:
        """读取现有 PID 文件中的进程 ID"""
        if not self.pid_file.exists():
            return None
        try:
            content = self.pid_file.read_text().strip()
            return int(content) if content.isdigit() else None
        except (ValueError, IOError):
            return None

    def _is_process_running(self, pid: int) -> bool:
        """检查进程是否仍在运行"""
        if sys.platform == "win32":
            # Windows: 使用 OpenProcess 检查
            PROCESS_QUERY_INFORMATION = 0x0400
            handle = _kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, False, pid)
            if handle:
                _kernel32.CloseHandle(handle)
                return True
            return False
        else:
            # Unix: 发送信号 0 检查
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False

    def _cleanup_stale_lock(self) -> bool:
        """清理过期锁文件"""
        existing_pid = self._read_existing_pid()
        if existing_pid is None:
            return True

        if not self._is_process_running(existing_pid):
            # 进程不存在，清理锁文件
            try:
                if sys.platform != "win32":
                    self.pid_file.unlink(missing_ok=True)
                return True
            except Exception:
                return False
        return False

    def _register_cleanup(self):
        """注册退出清理函数"""
        if self._cleanup_registered:
            return

        def cleanup():
            if self._locked:
                self.release()

        import atexit

        atexit.register(cleanup)
        self._cleanup_registered = True

    def acquire(self) -> bool:
        """
        获取单例锁

        返回:
            True: 成功获取锁，可以启动服务
            False: 锁已被占用，服务已在运行
        """
        if self._locked:
            return True

        # 检查端口占用
        if not self._check_port_available():
            logger.warning(
                "Service '%s' port %s:%s already in use",
                self.name,
                self.host,
                self.port,
            )
            return False

        # 清理过期锁
        if sys.platform != "win32" and not self._cleanup_stale_lock():
            logger.warning(
                "Service '%s' is already running (PID: %s)",
                self.name,
                self._read_existing_pid(),
            )
            return False

        # 获取锁
        if self._lock_impl.acquire():
            self._locked = True

            # 写入 PID 文件（仅 Windows）
            if sys.platform == "win32":
                try:
                    self.pid_dir.mkdir(parents=True, exist_ok=True)
                    self.pid_file.write_text(str(os.getpid()))
                except Exception:
                    pass

            # 注册自动清理
            if self.auto_cleanup:
                self._register_cleanup()

            logger.info("Service '%s' lock acquired (PID: %s)", self.name, os.getpid())
            return True

        return False

    def release(self) -> None:
        """释放单例锁"""
        if not self._locked:
            return

        self._lock_impl.release()
        self._locked = False

        # 清理 PID 文件
        if sys.platform == "win32":
            try:
                self.pid_file.unlink(missing_ok=True)
            except Exception:
                pass

        logger.info("Service '%s' lock released", self.name)

    def __enter__(self) -> "SingletonLock":
        """上下文管理器入口"""
        if not self.acquire():
            raise RuntimeError(
                f"Service '{self.name}' is already running. "
                f"Port {self.host}:{self.port} is in use or locked by another process."
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器退出"""
        self.release()

    def is_locked(self) -> bool:
        """检查是否持有锁"""
        return self._locked


@contextmanager
def singleton(
    name: str,
    pid_dir: Path | str | None = None,
    port: int | None = None,
    host: str = "127.0.0.1",
):
    """
    单例上下文管理器

    使用:
        with singleton("my_service", port=8080):
            # 服务代码
            ...
    """
    lock = SingletonLock(name, pid_dir, port, host)
    if not lock.acquire():
        raise RuntimeError(
            f"Service '{name}' is already running. "
            f"Check if port {host}:{port} is in use."
        )
    try:
        yield lock
    finally:
        lock.release()


def singleton_decorator(
    name: str | None = None,
    pid_dir: Path | str | None = None,
    port: int | None = None,
    host: str = "127.0.0.1",
):
    """
    单例装饰器 - 防止被装饰函数重复执行

    参数:
        name: 服务名称，默认使用函数名
        port: 可选，检查端口是否被占用

    使用:
        @singleton_decorator("my_service", port=8080)
        def main():
            ...
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            service_name = name or func.__name__
            lock = SingletonLock(service_name, pid_dir, port, host)

            if not lock.acquire():
                print(f"[ERROR] Service '{service_name}' is already running!")
                print(f"  Port {host}:{port} is in use or locked by another process.")
                print(f"  If you believe this is an error, delete the lock file:")
                print(f"    {lock.pid_file}")
                sys.exit(1)

            try:
                return func(*args, **kwargs)
            finally:
                lock.release()

        return wrapper

    return decorator


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """
    简单的端口占用检查工具函数

    返回:
        True: 端口已被占用
        False: 端口可用
    """
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


def get_lock_file_path(name: str, pid_dir: Path | str | None = None) -> Path:
    """获取指定服务的锁文件路径"""
    if pid_dir is None:
        project_root = Path(__file__).resolve().parents[3]
        pid_dir = project_root / "pids"
    return Path(pid_dir) / f"{name}.pid"
