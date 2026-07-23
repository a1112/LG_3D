import json
import os
import subprocess
import time
from pathlib import Path

import psutil


PROCESS_ATTRS = [
    'pid', 'name', 'exe', 'cmdline'
]


def normalize_path(path):
    if not path:
        return ""
    path = str(path).replace("file:///", "").strip().strip('"')
    return os.path.normcase(os.path.normpath(path))


def _cmdline_matches_targets(cmdline, target_paths):
    if not cmdline or not target_paths:
        return False
    normalized_items = {normalize_path(item) for item in cmdline if item}
    if normalized_items.intersection(target_paths):
        return True
    normalized_text = normalize_path(" ".join(str(item) for item in cmdline))
    return any(target and target in normalized_text for target in target_paths)


def get_listening_pids(port):
    try:
        target_port = int(port)
    except (TypeError, ValueError):
        return []
    if target_port <= 0:
        return []
    try:
        connections = psutil.net_connections(kind="inet")
    except (psutil.AccessDenied, OSError):
        return []
    result = set()
    for connection in connections:
        if connection.status != psutil.CONN_LISTEN or not connection.laddr:
            continue
        try:
            local_port = getattr(connection.laddr, "port", connection.laddr[1])
            process_id = int(connection.pid or 0)
        except (IndexError, TypeError, ValueError):
            continue
        if int(local_port) == target_port and process_id > 0:
            result.add(process_id)
    return sorted(result)


def get_process_ids_from_files(paths):
    result = set()
    for path in paths or []:
        try:
            text = Path(path).read_text(encoding="utf-8-sig").strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                payload = text
            process_id = int(payload.get("pid") if isinstance(payload, dict)
                             else payload)
            if process_id > 0 and psutil.pid_exists(process_id):
                result.add(process_id)
        except (OSError, TypeError, ValueError):
            continue
    return sorted(result)


def get_process_tree_roots(process_ids):
    """Return the highest service-owned Python/cmd parent for each PID."""
    protected = {os.getpid()}
    try:
        protected.update(parent.pid for parent in psutil.Process().parents())
    except (psutil.Error, OSError):
        pass

    allowed_parent_names = {"cmd.exe", "python.exe", "pythonw.exe"}
    roots = set()
    for process_id in {
            int(value) for value in process_ids or [] if int(value) > 0
    }:
        if not psutil.pid_exists(process_id):
            continue
        try:
            process = psutil.Process(process_id)
        except (psutil.Error, OSError):
            continue
        root = process
        for _ in range(5):
            try:
                parent = root.parent()
                parent_name = parent.name().casefold() if parent else ""
            except (psutil.Error, OSError):
                break
            if (parent is None or parent.pid in protected
                    or parent_name not in allowed_parent_names):
                break
            root = parent
        if root.pid not in protected:
            roots.add(root.pid)
    return sorted(roots)


def get_process(pid):
    """检查指定PID的进程是否正在运行"""
    try:
        # 尝试获取进程信息
        proc = psutil.Process(pid)
        # 这里可以通过proc.status()检查进程状态，但简单判断存在性即可
        # 即使进程存在，它可能处于僵尸状态等，但通常我们认为存在就是运行
        return proc
    except psutil.NoSuchProcess:
        return None

def kill_process_and_children(pid, timeout=5):
    if pid == os.getpid():
        return False
    try:
        parent = psutil.Process(pid)
    except psutil.NoSuchProcess:
        print(f"进程 {pid} 不存在")
        return False

    # 递归获取所有子进程
    try:
        children = parent.children(recursive=True)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        children = []

    processes = children + [parent]
    pids = {process.pid for process in processes}

    for process in processes:
        try:
            process.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    # 终止父进程
    try:
        parent.terminate()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

    _, alive = psutil.wait_procs(processes, timeout=timeout)
    for process in alive:
        try:
            process.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    _, alive = psutil.wait_procs(alive, timeout=2)

    for process in alive:
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            pass

    deadline = time.time() + 2
    while time.time() < deadline:
        if not any(psutil.pid_exists(pid) for pid in pids):
            return True
        time.sleep(0.1)
    return not any(psutil.pid_exists(pid) for pid in pids)


def getProcessDict(targets=None):
    process = getProcess(targets)
    processDict = {}
    for pro in process:
        exe = normalize_path(pro.get("exe"))
        if exe:
            processDict[exe] = pro
        cmdline = pro.get("cmdline") or []
        if pro.get("name") == "cmd.exe" and cmdline:
            cmd_target = normalize_path(cmdline[-1])
            if cmd_target:
                processDict[cmd_target] = pro
    return processDict


def getProcessesByTargets(targets):
    return getProcess(targets)


def getProcess(targets=None):
    processes = []
    target_paths = {normalize_path(target) for target in (targets or []) if target}
    target_names = {Path(target).name.lower() for target in target_paths if target}
    for process in psutil.process_iter():
        try:
            name = process.name()
            if target_names and name.lower() not in target_names and name != "cmd.exe":
                continue
            exe = process.exe()
            normalized_exe = normalize_path(exe)
            if target_paths and normalized_exe not in target_paths and name != "cmd.exe":
                continue
            process_info = {
                "pid": process.pid,
                "name": name,
                "exe": exe,
                "cmdline": []
            }
            if process_info["name"] == "cmd.exe":
                process_info["cmdline"] = process.cmdline()
                if target_paths and not _cmdline_matches_targets(process_info["cmdline"], target_paths):
                    continue
            processes.append(process_info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return processes


def toDict(process: psutil.Process):
    processDict = {}
    for attr in allAttrs:
        try:
            attrValue = getattr(process, attr)()
            processDict[attr] = attrValue
        except Exception as e:
            pass
    return processDict


allAttrs = PROCESS_ATTRS
