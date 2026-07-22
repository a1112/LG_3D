import json
import socket
import time
from pathlib import Path
from threading import Lock, Thread

import win32api
import win32gui
import psutil
from PySide6 import QtCore
from PySide6.QtCore import Slot

from MonitorBase.MonitorBase import MonitorBase
from ProcessObj import tryGetInt
from tools.soft import getProcessDict, getProcessesByTargets, kill_process_and_children, normalize_path

from configs.GlobSoftConfig import globSoftConfig
from enum_types.enums import SoftRunStateEnum


class SoftMonitor(MonitorBase):
    HEARTBEAT_RESTART_SECONDS = 200

    def __init__(self, parent=None):
        configF = "config/SoftMonitor.json"
        logFolder = "logs/SoftMonitor"
        super().__init__(configF, logFolder, parent, default_data=[])
        if not isinstance(self.monitorData, list):
            self.monitorData = []
            self.set_config_change(True)
        self.manualStopped = set()
        self.heartbeatFailedSince = {}
        self.heartbeatLastCheckedAt = {}
        self.restartLock = Lock()
        self.restarting = set()
        self.scanCompleted = False
        self.start()

    def _resolve_exe_path(self, exe):
        exe = str(exe or "").replace("file:///", "").strip().strip('"')
        if not exe:
            return ""
        exe_path = Path(exe)
        if exe_path.is_absolute():
            return str(exe_path)
        return str(Path(self.configFile).resolve().parent / exe_path)

    def _start_exe_(self, exe, args):
        exe = self._resolve_exe_path(exe)
        args = str(args or "")
        self.log.info(f"执行 \"{exe}\" {args}")
        exe_url = Path(exe)
        try:
            pid = win32api.ShellExecute(win32gui.GetDesktopWindow(), 'runas', exe, args, str(exe_url.parent), 1)
            if pid <= 32:
                self.log.error(f"启动失败 {exe} {args} ShellExecute={pid}")
            return pid
        except BaseException as e:
            self.log.error(f"启动异常 {exe} {args} {e}")
            return 0

    def _heartbeat_healthy(self, item):
        port = tryGetInt(item.get("heartbeatPort", 0))
        if port <= 0:
            return True
        host = str(item.get("heartbeatHost", "127.0.0.1"))
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except (OSError, ValueError):
            return False

    def _check_heartbeat(self, item):
        name = item.get("name", "")
        port = tryGetInt(item.get("heartbeatPort", 0))
        if port <= 0:
            self.heartbeatFailedSince.pop(name, None)
            self.heartbeatLastCheckedAt.pop(name, None)
            return
        self.heartbeatLastCheckedAt[name] = time.time()
        if self._heartbeat_healthy(item):
            if name in self.heartbeatFailedSince:
                self.log.info(f"{name} heartbeat recovered")
            self.heartbeatFailedSince.pop(name, None)
            return

        now = time.monotonic()
        timeout_seconds = max(
            tryGetInt(item.get("heartbeatTimeoutSeconds",
                               self.HEARTBEAT_RESTART_SECONDS)), 1)
        failed_since = self.heartbeatFailedSince.setdefault(name, now)
        failed_seconds = now - failed_since
        if failed_seconds < timeout_seconds:
            return
        self.log.error(
            f"{name} heartbeat failed for {int(failed_seconds)} seconds; "
            f"timeout={timeout_seconds}; restarting")
        self.heartbeatFailedSince[name] = now
        self.restartExe(name)
        # return 0

        # # Windows 特定标志
        # creationflags = 0
        # if sys.platform == "win32":
        #     # 使用以下标志确保子进程独立运行
        #     creationflags = (
        #             subprocess.CREATE_NEW_PROCESS_GROUP |
        #             subprocess.DETACHED_PROCESS |
        #             subprocess.CREATE_NO_WINDOW  # 可选：隐藏控制台窗口
        #     )
        #
        # # 启动程序（不等待结束）
        # process = subprocess.Popen(
        #     [exe, args],
        #     shell=False  # 重要：设置为 False
        # )

    # 立即返回，不等待程序结束
    # Python 脚本可以继续执行或直接退出

    @Slot(str, result=int)
    def getState_(self, name):
        if name in self.stateDict:
            return self.stateDict[name]
        return -2

    @Slot(str, result=bool)
    def stopExe(self, exe):
        normalized_exe = normalize_path(self._resolve_exe_path(exe))
        name = Path(str(exe)).name
        self.log.debug(f"主动关闭 {name} {exe}")
        self.manualStopped.add(normalized_exe)
        return self._stop_target(normalized_exe, name)

    def _get_target_pids(self, normalized_exe):
        pid_list = [
            pid for pid in globSoftConfig.get_pid_list(normalized_exe)
            if psutil.pid_exists(pid)
        ]
        pid_list.extend(
            process["pid"]
            for process in getProcessesByTargets([normalized_exe])
            if process.get("pid")
        )
        return sorted(set(pid_list))

    def _stop_target(self, normalized_exe, name=""):
        stopped = False
        for _ in range(3):
            pid_list = self._get_target_pids(normalized_exe)
            if not pid_list:
                stopped = True
                break
            for pid in pid_list:
                stopped = kill_process_and_children(pid) or stopped
            time.sleep(0.5)

        remaining = self._get_target_pids(normalized_exe)
        if remaining:
            self.log.error(f"关闭失败，仍有残留进程 {name or normalized_exe}: {remaining}")
            return False

        if stopped:
            for item in list(self.monitorData):
                item_exe = normalize_path(
                    self._resolve_exe_path(item.get("exe", "")))
                if item_exe == normalized_exe:
                    self.stateDict[item.get("name", name)] = SoftRunStateEnum.STOPPED
                    globSoftConfig.set_soft_state(normalized_exe, 0, SoftRunStateEnum.STOPPED)
        return True

    @Slot(int, str, str)
    @Slot(int, str, bool)
    @Slot(int, str, int)
    def changeValue(self, index, key, value):
        self.log.info(f"修改 {index} {key} {value}")
        self.monitorData[index][key] = value
        self.set_config_change(self.monitorData != self.monitorData_old)

    @Slot(str, result=bool)
    def startExe(self, name):
        normalized_target = normalize_path(name)
        for item in list(self.monitorData):
            item_name = item.get("name", "")
            exe = self._resolve_exe_path(item.get("exe", ""))
            if name == item_name or normalized_target == normalize_path(exe):
                args = item["args"] if "args" in item else ""
                self.manualStopped.discard(normalize_path(exe))
                self.log.debug("主动启动 " + item_name + " " + exe + " " + args)
                self._start_exe_(item.get("exe", ""), args)
                return True
        return False

    def _find_monitor_item(self, name):
        normalized_target = normalize_path(name)
        for item in list(self.monitorData):
            item_name = item.get("name", "")
            exe = normalize_path(
                self._resolve_exe_path(item.get("exe", "")))
            if name == item_name or normalized_target == exe:
                return item, exe
        return None, ""

    def _restart_exe_worker(self, item, exe):
        item_name = item.get("name", "")
        try:
            self.log.info(f"后台重启 {item_name} {exe}")
            self.manualStopped.add(exe)
            if not self._stop_target(exe, item_name):
                return
            time.sleep(1)
            self.manualStopped.discard(exe)
            result = self._start_exe_(item.get("exe", ""),
                                      item.get("args", ""))
            if result <= 32:
                self.log.error(f"重启后启动失败 {item_name} {exe}")
        except Exception as e:
            self.log.error(f"后台重启异常 {item_name} {exe}: {e}")
        finally:
            self.manualStopped.discard(exe)
            with self.restartLock:
                self.restarting.discard(exe)

    @Slot(str, result=bool)
    def restartExe(self, name):
        item, exe = self._find_monitor_item(name)
        if item is None:
            return False
        with self.restartLock:
            if exe in self.restarting:
                self.log.warning(f"服务正在重启，忽略重复请求 {name}")
                return False
            self.restarting.add(exe)
        try:
            Thread(target=self._restart_exe_worker,
                   args=(dict(item), exe),
                   name=f"service-restart-{item.get('name', 'unknown')}",
                   daemon=True).start()
        except Exception:
            with self.restartLock:
                self.restarting.discard(exe)
            raise
        return True

    @Slot(result=bool)
    def closeAll(self):
        self.log.debug("全部关闭。")
        ok = True
        for item in list(self.monitorData):
            exe = normalize_path(self._resolve_exe_path(item.get("exe", "")))
            if not exe:
                continue
            self.manualStopped.add(exe)
            ok = self._stop_target(exe, item.get("name", "")) and ok
        return ok

    @Slot(result=bool)
    def startAll(self):
        self.log.debug("全部启动。 ")
        processDict = getProcessDict([self._resolve_exe_path(item.get("exe", "")) for item in self.monitorData])
        started = False
        for item in list(self.monitorData):
            exe = normalize_path(self._resolve_exe_path(item["exe"]))
            if exe in processDict:
                continue
            args = item["args"] if "args" in item else ""
            monitor = item["monitorAble"] if "monitorAble" in item else True
            if monitor:
                self.manualStopped.discard(exe)
                self._start_exe_(item.get("exe", ""), args)
                started = True
        return started

    def _restart_all_worker(self, restart_items):
        self.log.debug("全部重启。")
        ok = True
        try:
            for item, exe in restart_items:
                self.manualStopped.add(exe)
                ok = self._stop_target(exe, item.get("name", "")) and ok
            time.sleep(1)
            for item, exe in restart_items:
                if self._get_target_pids(exe):
                    self.log.error(
                        f"跳过启动，进程仍未清理干净 {item.get('name', exe)}")
                    ok = False
                    continue
                self.manualStopped.discard(exe)
                self._start_exe_(item.get("exe", ""), item.get("args", ""))
        except Exception as e:
            self.log.error(f"后台全部重启异常: {e}")
            ok = False
        finally:
            with self.restartLock:
                for _, exe in restart_items:
                    self.manualStopped.discard(exe)
                    self.restarting.discard(exe)
        return ok

    @Slot(result=bool)
    def restartAll(self):
        restart_items = []
        for item in list(self.monitorData):
            exe = normalize_path(self._resolve_exe_path(item.get("exe", "")))
            if exe and item.get("monitorAble", True):
                restart_items.append((dict(item), exe))
        if not restart_items:
            return False
        with self.restartLock:
            if self.restarting:
                self.log.warning("已有服务正在重启，忽略全部重启请求")
                return False
            self.restarting.update(exe for _, exe in restart_items)
        Thread(target=self._restart_all_worker,
               args=(restart_items,),
               name="service-restart-all",
               daemon=True).start()
        return True

    @Slot(result=str)
    def getIssues(self):
        if not self.scanCompleted:
            return "[]"
        issues = []
        for item in list(self.monitorData):
            name = item.get("name", "")
            if not item.get("monitorAble", True):
                continue
            exe = normalize_path(
                self._resolve_exe_path(item.get("exe", "")))
            if exe in self.manualStopped:
                continue
            state = self.stateDict.get(name, -2)
            heartbeat_failed_since = self.heartbeatFailedSince.get(name)
            if heartbeat_failed_since is not None:
                failed_seconds = int(time.monotonic() - heartbeat_failed_since)
                issues.append({
                    "name": name,
                    "exe": item.get("exe", ""),
                    "state": state,
                    "message": (
                        f"heartbeat failed for {failed_seconds}/"
                        f"{max(tryGetInt(item.get('heartbeatTimeoutSeconds', self.HEARTBEAT_RESTART_SECONDS)), 1)} seconds"
                    ),
                })
                continue
            if state == SoftRunStateEnum.RUNNING:
                continue
            issues.append({
                "name": name,
                "exe": item.get("exe", ""),
                "state": state,
                "message": "启动文件不存在" if state == SoftRunStateEnum.NULL else "服务未运行",
            })
        return json.dumps(issues, ensure_ascii=False)

    @Slot(str, result=QtCore.QJsonValue)
    def getDefault(self, exe: str):
        exe = exe.replace("file:///", "")
        return {
            "name": Path(exe).stem,
            "exe": exe,
            "args": "",
            "delay": 5,
            "monitorAble": True
        }

    @Slot(QtCore.QJsonValue)
    def addApp(self, app: QtCore.QJsonValue):
        app = app.toVariant()
        self.log.debug("添加数据" + json.dumps(app, indent=4, ensure_ascii=False))
        app["delay"] = tryGetInt(app["delay"])

        self.monitorData.append(app)
        self.set_config_change(True)

    @Slot(int)
    def remove(self, index):
        self.log.debug("移除数据" + json.dumps(self.monitorData[index], indent=4, ensure_ascii=False))
        self.monitorData.pop(index)
        self.set_config_change(True)

    @Slot(int, result=dict)
    def index(self, index):
        return self.monitorData[index]

    def run(self):
        while self._running:
            try:
                processDict = getProcessDict([self._resolve_exe_path(item.get("exe", "")) for item in self.monitorData])
            except Exception as e:
                self.log.error(f"获取进程列表失败 {e}")
                time.sleep(5)
                continue
            for item in list(self.monitorData):
                name = item.get("name", "")
                exe_path = self._resolve_exe_path(item.get("exe", ""))
                exe = normalize_path(exe_path)
                args = item["args"] if "args" in item else ""
                delay = tryGetInt(item["delay"]) if "delay" in item else 5
                monitor = item["monitorAble"] if "monitorAble" in item else True

                pid = 0
                if not exe or not Path(exe_path).exists():
                    self.log.error(f"{name}  不存在 {exe_path} {args}  延时 {delay}")
                    self.stateDict[name] = SoftRunStateEnum.NULL
                    continue
                if exe not in processDict:
                    self.stateDict[name] = SoftRunStateEnum.STOPPED
                    self.log.debug(f"{name}  未运行  {exe} {args}  延时 {delay}  监听 {monitor}")
                    if monitor and exe not in self.manualStopped:
                        time.sleep(delay)
                        self.log.debug(f"{name}  启动  {exe} {args}  延时 {delay}  监听 {monitor}")
                        self._start_exe_(exe, args)
                        self.stateDict[name] = SoftRunStateEnum.RUNNING
                    continue
                else:
                    process = processDict[exe]
                    pid = process.get("pid", 0)
                    self.stateDict[name] = SoftRunStateEnum.RUNNING
                globSoftConfig.set_soft_state(exe, pid, self.stateDict[name])
                self._check_heartbeat(item)

                # 运行该软件
            self.scanCompleted = True
            time.sleep(10)

    @Slot(str, result=str)
    def getHeartbeatText(self, name):
        item, _ = self._find_monitor_item(name)
        if item is None:
            return ""
        port = tryGetInt(item.get("heartbeatPort", 0))
        if port <= 0:
            return ""
        host = str(item.get("heartbeatHost", "127.0.0.1"))
        timeout_seconds = max(
            tryGetInt(item.get("heartbeatTimeoutSeconds",
                               self.HEARTBEAT_RESTART_SECONDS)), 1)
        checked_at = self.heartbeatLastCheckedAt.get(name)
        checked_text = (time.strftime("%H:%M:%S", time.localtime(checked_at))
                        if checked_at else "等待首次检测")
        failed_since = self.heartbeatFailedSince.get(name)
        if failed_since is not None:
            failed_seconds = max(int(time.monotonic() - failed_since), 0)
            return (f"心跳 {host}:{port} 异常 {failed_seconds}/{timeout_seconds}s "
                    f"· 最近检测 {checked_text}")
        return (f"心跳 {host}:{port} 正常 · 最近检测 {checked_text} "
                f"· 超时 {timeout_seconds}s")
