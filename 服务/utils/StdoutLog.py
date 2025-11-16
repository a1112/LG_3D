import os
import sys
from datetime import datetime
from pathlib import Path


class Logger:
    def __init__(self, log_key: str = "base"):
        self.current_date = None
        self.log_file = None
        self.log_key = log_key
        self.original_stdout = sys.stdout
        # On Windows uvicorn/event-loop combos can crash when stdout is replaced.
        # Allow opting out via env; default disable on Windows, enable elsewhere.
        env_val = os.getenv("ENABLE_STDOUT_REDIRECT")
        default_redirect = "0" if os.name == "nt" else "1"
        self.enable_redirect = str(env_val or default_redirect).strip().lower() not in {"0", "false", "no", "off"}
        if self.enable_redirect:
            self._open_log_file()

    def _open_log_file(self):
        # 获取当前日期并判断是否需要切换文件
        new_date = datetime.now().strftime("%Y-%m-%d")

        # 如果当前日期与日志文件日期不符，重新打开一个新的日志文件
        if new_date != self.current_date:
            self.current_date = new_date
            if self.log_file:
                self.log_file.close()  # 关闭之前的文件
            # 创建新的日志文件
            log_folder = Path("log") / "stdout" / self.log_key
            log_folder.mkdir(parents=True, exist_ok=True)
            self.log_file = open(log_folder / f"{self.current_date}.log", "a", encoding="utf-8")

        # 重定向 stdout 到当前日志文件
        sys.stdout = self

    def write(self, message):
        if not self.enable_redirect:
            self.original_stdout.write(message)
            return
        # 每次写入时检查是否需要更换文件
        self._open_log_file()

        # 输出到控制台
        self.original_stdout.write(message)

        # 写入文件
        self.log_file.write(message)

    def flush(self):
        # 刷新缓冲区，确保数据写入
        if self.log_file:
            self.log_file.flush()

    def close(self):
        # 关闭文件并恢复 stdout
        if self.log_file:
            self.log_file.close()
        sys.stdout = self.original_stdout

    # 代理原始 stdout 的属性和方法
    def __getattr__(self, name):
        return getattr(self.original_stdout, name)

# 示例使用
