import base64
import json
import os
import socket
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import psutil


_SAMPLE_LOCK = threading.Lock()
_LAST_SAMPLES: dict[str, tuple[float, int, int]] = {}
_WINDOWS_LINK_SPEED_LOCK = threading.Lock()
_WINDOWS_LINK_SPEED_CACHE: tuple[float, dict[str, int]] = (0.0, {})
_WINDOWS_LINK_SPEED_REFRESHING = False
_WINDOWS_LINK_SPEED_CACHE_SECONDS = 60.0
_CONTROL_ACTIONS = {
    "enable": "Enable-NetAdapter",
    "disable": "Disable-NetAdapter",
    "restart": "Restart-NetAdapter",
}
_SERVICE_DEFINITIONS = (
    {
        "key": "main_api",
        "name": "主 API",
        "category": "核心",
        "port": 5010,
        "commandTokens": ("server.py",),
        "cwdFragment": "/app/server",
        "restartLauncher": "start_lg3d_api_source.bat",
    },
    {
        "key": "capture",
        "name": "3D / 2D 采集",
        "category": "核心",
        "port": 6100,
        "commandTokens": ("capall.py",),
        "cwdFragment": "/app/captrue",
        "restartLauncher": "start_lg3d_capture_3d_source.bat",
    },
    {
        "key": "algorithm_3d",
        "name": "3D 算法",
        "category": "算法",
        "commandTokens": ("main.py",),
        "cwdFragment": "/app/algorithm_runtime",
        "restartLauncher": "start_lg3d_algorithm_3d_source.bat",
    },
    {
        "key": "algorithm_2d",
        "name": "2D 算法",
        "category": "算法",
        "port": 6020,
        "commandTokens": ("server.py",),
        "cwdFragment": "/app/algorithm_runtime_2d",
        "restartLauncher": "start_lg3d_algorithm_2d_source.bat",
    },
    {
        "key": "secondary_tcp",
        "name": "二级 TCP",
        "category": "通信",
        "port": 6001,
        "commandTokens": ("tcpserver.py",),
        "cwdFragment": "/app/communication",
        "restartLauncher": "start_lg3d_secondary_tcp_source.bat",
    },
    {
        "key": "plc_write",
        "name": "PLC 写入",
        "category": "通信",
        "commandTokens": ("writeplc.py",),
        "cwdFragment": "/app/plcserver",
        "restartLauncher": "start_lg3d_plc_write_source.bat",
    },
    {
        "key": "rust_api",
        "name": "Rust 数据 API",
        "category": "加速",
        "port": 5011,
        "processNames": ("rust_api_service.exe",),
    },
    {
        "key": "rust_image",
        "name": "Rust 图像服务",
        "category": "加速",
        "port": 6013,
        "processNames": ("rust_image_service_v2.exe",),
    },
    {
        "key": "redis",
        "name": "Redis",
        "category": "基础",
        "port": 6379,
        "processNames": ("redis-server.exe",),
    },
    {
        "key": "lis_watchdog",
        "name": "LIS 服务守护",
        "category": "守护",
        "processNames": ("lis.exe",),
    },
)


def _service_definition(service_key: str) -> dict:
    for definition in _SERVICE_DEFINITIONS:
        if definition["key"] == service_key:
            return definition
    raise LookupError(f"unknown service: {service_key}")


def _launcher_directories() -> list[Path]:
    configured = os.getenv("LG3D_SERVICE_LAUNCHER_DIR", "").strip()
    project_root = Path(__file__).resolve().parents[3]
    candidates = []
    if configured:
        candidates.append(Path(configured))
    candidates.extend((
        project_root.parent / "bkvl_UI" / "config" / "launchers",
        project_root.parent / "bkvl_UI" / "dist" / "lis" / "config" / "launchers",
    ))
    return candidates


def _resolve_restart_launcher(definition: dict) -> Path | None:
    launcher_name = definition.get("restartLauncher")
    if not launcher_name:
        return None
    for directory in _launcher_directories():
        launcher = directory / launcher_name
        if launcher.is_file():
            return launcher.resolve()
    return None


def _schedule_service_restart(process_ids: list[int], launcher: Path) -> None:
    pid_values = ",".join(str(pid) for pid in sorted(set(process_ids)) if pid > 0)
    escaped_launcher = str(launcher).replace("'", "''")
    escaped_workdir = str(launcher.parent).replace("'", "''")
    script = (
        "$ErrorActionPreference='Continue';"
        "Start-Sleep -Seconds 1;"
        f"$targets=@({pid_values});"
        "foreach($targetPid in $targets){"
        "Stop-Process -Id $targetPid -Force -ErrorAction SilentlyContinue};"
        "Start-Sleep -Seconds 1;"
        f"Start-Process -FilePath '{escaped_launcher}' "
        f"-WorkingDirectory '{escaped_workdir}'"
    )
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    creation_flags = (
        getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        | getattr(subprocess, "DETACHED_PROCESS", 0)
        | getattr(subprocess, "CREATE_NO_WINDOW", 0)
    )
    subprocess.Popen(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-WindowStyle",
         "Hidden", "-EncodedCommand", encoded],
        close_fds=True,
        creationflags=creation_flags,
    )


def restart_service(service_key: str) -> dict:
    definition = _service_definition(service_key)
    launcher = _resolve_restart_launcher(definition)
    if launcher is None:
        raise RuntimeError(f"restart launcher unavailable for {service_key}")

    snapshots = _process_snapshots()
    listeners = _listening_pids_by_port()
    process_ids = [
        snapshot["pid"] for snapshot in snapshots.values()
        if _process_matches_service(snapshot, definition)
    ]
    port = int(definition.get("port") or 0)
    if port:
        process_ids.extend(listeners.get(port, set()))
    _schedule_service_restart(process_ids, launcher)
    return {
        "ok": True,
        "serviceKey": service_key,
        "serviceName": definition["name"],
        "message": "restart scheduled",
    }


def _duplex_name(value: int) -> str:
    duplex_names = {
        getattr(psutil, "NIC_DUPLEX_FULL", -1): "full",
        getattr(psutil, "NIC_DUPLEX_HALF", -2): "half",
        getattr(psutil, "NIC_DUPLEX_UNKNOWN", -3): "unknown",
    }
    return duplex_names.get(value, "unknown")


def _address_family_name(family: Any) -> str:
    if family == socket.AF_INET:
        return "ipv4"
    if family == socket.AF_INET6:
        return "ipv6"
    if family == getattr(psutil, "AF_LINK", object()):
        return "mac"
    return str(family)


def _adapter_addresses(addresses) -> tuple[list[dict], list[str], list[str], str]:
    address_items = []
    ipv4 = []
    ipv6 = []
    mac = ""
    for address in addresses:
        family = _address_family_name(address.family)
        value = address.address or ""
        item = {
            "family": family,
            "address": value,
            "netmask": address.netmask or "",
            "broadcast": address.broadcast or "",
        }
        if hasattr(address, "ptp"):
            item["ptp"] = address.ptp or ""
        address_items.append(item)
        if family == "ipv4":
            ipv4.append(value)
        elif family == "ipv6":
            ipv6.append(value.split("%", 1)[0])
        elif family == "mac" and not mac:
            mac = value
    return address_items, ipv4, ipv6, mac


def _throughput(name: str, counters, sampled_at: float) -> tuple[float, float, float]:
    if counters is None:
        return 0.0, 0.0, 0.0

    sent = int(getattr(counters, "bytes_sent", 0))
    received = int(getattr(counters, "bytes_recv", 0))
    previous = _LAST_SAMPLES.get(name)
    _LAST_SAMPLES[name] = (sampled_at, sent, received)
    if previous is None:
        return 0.0, 0.0, 0.0

    previous_time, previous_sent, previous_received = previous
    interval = max(sampled_at - previous_time, 0.0)
    if interval <= 0:
        return 0.0, 0.0, 0.0
    tx_bps = max(sent - previous_sent, 0) / interval
    rx_bps = max(received - previous_received, 0) / interval
    return rx_bps, tx_bps, interval


def _refresh_windows_link_speeds() -> None:
    global _WINDOWS_LINK_SPEED_CACHE
    global _WINDOWS_LINK_SPEED_REFRESHING

    script = (
        "$ErrorActionPreference = 'Stop';"
        "[Console]::OutputEncoding = [Text.Encoding]::UTF8;"
        "Get-CimInstance -Namespace root/StandardCimv2 "
        "-ClassName MSFT_NetAdapter | "
        "Select-Object Name,TransmitLinkSpeed,ReceiveLinkSpeed | "
        "ConvertTo-Json -Compress")
    speeds: dict[str, int] = {}
    try:
        result = _run_powershell(script, timeout=5)
        if result.returncode == 0:
            raw_payload = (result.stdout or "").lstrip("\ufeff").strip()
            payload = json.loads(raw_payload or "[]")
            if isinstance(payload, dict):
                payload = [payload]
            for item in payload:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("Name") or "")
                transmit = int(item.get("TransmitLinkSpeed") or 0)
                receive = int(item.get("ReceiveLinkSpeed") or 0)
                speed_bps = max(transmit, receive)
                if name and speed_bps > 0:
                    speeds[name] = round(speed_bps / 1_000_000)
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        speeds = {}
    finally:
        with _WINDOWS_LINK_SPEED_LOCK:
            _WINDOWS_LINK_SPEED_CACHE = (time.monotonic(), speeds)
            _WINDOWS_LINK_SPEED_REFRESHING = False


def _windows_link_speeds() -> dict[str, int]:
    """Return cached native Windows link speeds in Mbps without blocking.

    psutil reports 4294 Mbps for some links faster than 4 Gbps on Windows
    because the value is capped at an unsigned 32-bit sentinel. A short-lived
    background query preserves the full 64-bit link speed without delaying
    the status endpoint.
    """
    global _WINDOWS_LINK_SPEED_REFRESHING

    if os.name != "nt":
        return {}

    sampled_at = time.monotonic()
    with _WINDOWS_LINK_SPEED_LOCK:
        cached_at, cached_speeds = _WINDOWS_LINK_SPEED_CACHE
        cache_expired = (
            sampled_at - cached_at >= _WINDOWS_LINK_SPEED_CACHE_SECONDS)
        if cache_expired and not _WINDOWS_LINK_SPEED_REFRESHING:
            _WINDOWS_LINK_SPEED_REFRESHING = True
            threading.Thread(
                target=_refresh_windows_link_speeds,
                name="network-link-speed-monitor",
                daemon=True,
            ).start()
        return dict(cached_speeds)


def get_network_adapters() -> list[dict]:
    stats_by_name = psutil.net_if_stats() or {}
    addresses_by_name = psutil.net_if_addrs() or {}
    counters_by_name = psutil.net_io_counters(pernic=True) or {}
    names = set(stats_by_name) | set(addresses_by_name) | set(counters_by_name)
    native_link_speeds = {}
    if os.name == "nt" and any(
            int(getattr(stats, "speed", 0) or 0) == 4294
            for stats in stats_by_name.values()):
        native_link_speeds = _windows_link_speeds()
    sampled_at = time.monotonic()
    can_control = os.name == "nt"
    adapters = []

    with _SAMPLE_LOCK:
        missing_names = set(_LAST_SAMPLES) - names
        for missing_name in missing_names:
            _LAST_SAMPLES.pop(missing_name, None)

        for name in names:
            stats = stats_by_name.get(name)
            counters = counters_by_name.get(name)
            addresses, ipv4, ipv6, mac = _adapter_addresses(
                addresses_by_name.get(name, []))
            rx_bps, tx_bps, sample_interval = _throughput(
                name, counters, sampled_at)
            is_up = bool(getattr(stats, "isup", False))
            is_loopback = (any(address.startswith("127.") for address in ipv4)
                           or any(address == "::1" for address in ipv6)
                           or "loopback" in name.lower())
            adapter_can_control = can_control and not is_loopback
            counter_value = counters or object()
            adapters.append({
                "name":
                name,
                "isUp":
                is_up,
                "status":
                "up" if is_up else "down",
                "speedMbps":
                native_link_speeds.get(
                    name, int(getattr(stats, "speed", 0) or 0)),
                "mtu":
                int(getattr(stats, "mtu", 0) or 0),
                "duplex":
                _duplex_name(getattr(stats, "duplex", -1)),
                "mac":
                mac,
                "ipv4":
                ipv4,
                "ipv6":
                ipv6,
                "addresses":
                addresses,
                "bytesSent":
                int(getattr(counter_value, "bytes_sent", 0)),
                "bytesReceived":
                int(getattr(counter_value, "bytes_recv", 0)),
                "packetsSent":
                int(getattr(counter_value, "packets_sent", 0)),
                "packetsReceived":
                int(getattr(counter_value, "packets_recv", 0)),
                "errorsIn":
                int(getattr(counter_value, "errin", 0)),
                "errorsOut":
                int(getattr(counter_value, "errout", 0)),
                "dropsIn":
                int(getattr(counter_value, "dropin", 0)),
                "dropsOut":
                int(getattr(counter_value, "dropout", 0)),
                "rxBytesPerSecond":
                rx_bps,
                "txBytesPerSecond":
                tx_bps,
                "sampleInterval":
                sample_interval,
                "isLoopback":
                is_loopback,
                "canControl":
                adapter_can_control,
                "controlReason":
                "" if adapter_can_control else (
                    "loopback adapter cannot be controlled"
                    if is_loopback else
                    "network adapter control is only supported on Windows"),
            })

    adapters.sort(key=lambda item: (not item["isUp"], item["name"].lower()))
    return adapters


def _normalize_process_text(value: Any) -> str:
    return str(value or "").replace("\\", "/").casefold()


def _process_snapshots() -> dict[int, dict]:
    snapshots = {}
    attrs = ["pid", "name", "cmdline", "create_time", "memory_info"]
    for process in psutil.process_iter(attrs):
        try:
            info = process.info
            pid = int(info.get("pid") or 0)
            if pid <= 0:
                continue
            cmdline_parts = info.get("cmdline") or []
            command_line = " ".join(str(part) for part in cmdline_parts)
            try:
                cwd = process.cwd()
            except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
                cwd = ""
            memory_info = info.get("memory_info")
            snapshots[pid] = {
                "pid": pid,
                "processName": str(info.get("name") or ""),
                "commandLine": command_line[:320],
                "commandText": _normalize_process_text(command_line),
                "cwd": str(cwd or ""),
                "cwdText": _normalize_process_text(cwd),
                "startedAt": float(info.get("create_time") or 0),
                "memoryBytes": int(getattr(memory_info, "rss", 0) or 0),
            }
        except (psutil.AccessDenied, psutil.NoSuchProcess, OSError,
                TypeError, ValueError):
            continue
    return snapshots


def _listening_pids_by_port() -> dict[int, set[int]]:
    listeners: dict[int, set[int]] = {}
    try:
        connections = psutil.net_connections(kind="inet")
    except (psutil.AccessDenied, OSError):
        return listeners
    for connection in connections:
        if connection.status != psutil.CONN_LISTEN or not connection.laddr:
            continue
        try:
            port_value = getattr(connection.laddr, "port", None)
            if port_value is None:
                port_value = connection.laddr[1]
            port = int(port_value)
            pid = int(connection.pid or 0)
        except (IndexError, TypeError, ValueError):
            continue
        listeners.setdefault(port, set())
        if pid > 0:
            listeners[port].add(pid)
    return listeners


def _process_matches_service(snapshot: dict, definition: dict) -> bool:
    process_names = tuple(
        str(name).casefold()
        for name in definition.get("processNames", ()))
    command_tokens = tuple(
        str(token).casefold()
        for token in definition.get("commandTokens", ()))
    cwd_fragment = _normalize_process_text(
        definition.get("cwdFragment", ""))

    if process_names and snapshot["processName"].casefold() not in process_names:
        return False
    if command_tokens and not all(
            token in snapshot["commandText"] for token in command_tokens):
        return False
    if cwd_fragment and cwd_fragment not in snapshot["cwdText"]:
        return False
    return bool(process_names or command_tokens or cwd_fragment)


def get_service_statuses() -> list[dict]:
    sampled_at = time.time()
    snapshots = _process_snapshots()
    listeners = _listening_pids_by_port()
    services = []

    for definition in _SERVICE_DEFINITIONS:
        port = int(definition.get("port") or 0)
        listener_pids = sorted(listeners.get(port, set())) if port else []
        matched = [
            snapshot for snapshot in snapshots.values()
            if _process_matches_service(snapshot, definition)
        ]
        if listener_pids:
            listener_matches = [
                snapshots[pid] for pid in listener_pids if pid in snapshots
            ]
            if listener_matches:
                matched = listener_matches + [
                    item for item in matched
                    if item["pid"] not in listener_pids
                ]

        process = matched[0] if matched else None
        process_running = process is not None
        online = bool(listener_pids) if port else process_running
        state = ("running" if online else
                 "starting" if process_running else "stopped")
        started_at = process.get("startedAt", 0) if process else 0
        services.append({
            "key":
            definition["key"],
            "name":
            definition["name"],
            "category":
            definition["category"],
            "canRestart":
            _resolve_restart_launcher(definition) is not None,
            "online":
            online,
            "state":
            state,
            "stateText":
            "运行中" if online else "启动中" if process_running else "未运行",
            "host":
            "127.0.0.1",
            "port":
            port or None,
            "pid":
            process.get("pid") if process else (
                listener_pids[0] if listener_pids else None),
            "processName":
            process.get("processName", "") if process else "",
            "commandLine":
            process.get("commandLine", "") if process else "",
            "startedAt":
            started_at,
            "uptimeSeconds":
            max(sampled_at - started_at, 0) if started_at else None,
            "memoryBytes":
            process.get("memoryBytes", 0) if process else 0,
            "listenerPids":
            listener_pids,
            "processCount":
            len(matched),
            "message": (
                f"监听 127.0.0.1:{port}" if online and port else
                "进程运行中" if online else
                f"进程已启动，等待端口 {port}" if process_running and port
                else "未检测到进程"),
        })
    return services


def _powershell_script(adapter_name: str, action: str) -> str:
    command = _CONTROL_ACTIONS[action]
    encoded_name = base64.b64encode(adapter_name.encode("utf-8")).decode("ascii")
    return (
        "$ErrorActionPreference = 'Stop';"
        "[Console]::OutputEncoding = [Text.Encoding]::UTF8;"
        f"$name = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded_name}'));"
        "$adapter = @(Get-NetAdapter -ErrorAction Stop | "
        "Where-Object { $_.Name -ceq $name });"
        "if ($adapter.Count -ne 1) { throw \"network adapter not found or ambiguous: $name\" };"
        f"$adapter | {command} -Confirm:$false -ErrorAction Stop;"
        "$adapter | Select-Object Name, Status, LinkSpeed | ConvertTo-Json -Compress")


def _run_powershell(
        script: str,
        timeout: float = 20,
) -> subprocess.CompletedProcess:
    encoded_script = base64.b64encode(
        script.encode("utf-16-le")).decode("ascii")
    return subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-EncodedCommand",
            encoded_script,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def control_network_adapter(adapter_name: str, action: str) -> dict:
    normalized_action = action.strip().lower()
    if normalized_action not in _CONTROL_ACTIONS:
        allowed = ", ".join(sorted(_CONTROL_ACTIONS))
        raise ValueError(f"unsupported action: {action}; allowed: {allowed}")
    if os.name != "nt":
        raise RuntimeError("network adapter control is only supported on Windows")

    known_names = {
        *psutil.net_if_stats().keys(),
        *psutil.net_if_addrs().keys(),
    }
    if adapter_name not in known_names:
        raise LookupError(f"network adapter not found: {adapter_name}")
    adapter = next(
        (item for item in get_network_adapters()
         if item["name"] == adapter_name),
        None,
    )
    if adapter is None:
        raise LookupError(f"network adapter not found: {adapter_name}")
    if adapter.get("isLoopback", False):
        raise ValueError("loopback adapter cannot be controlled")

    try:
        result = _run_powershell(
            _powershell_script(adapter_name, normalized_action))
    except (OSError, subprocess.SubprocessError) as e:
        raise RuntimeError(
            f"{normalized_action} network adapter failed: {e}") from e
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "unknown error").strip()
        raise RuntimeError(
            f"{normalized_action} network adapter failed: {detail}")

    return {
        "ok": True,
        "adapterName": adapter_name,
        "action": normalized_action,
        "message": f"{normalized_action} command completed",
        "commandOutput": result.stdout.strip(),
    }
