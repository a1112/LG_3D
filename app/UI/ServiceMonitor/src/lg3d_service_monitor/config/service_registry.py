import json
from pathlib import Path
from typing import Any

from .paths import bundled_registry_path, service_registry_path


REQUIRED_SERVICE_KEYS = {
    "key",
    "name",
    "launcher",
}


def _registry_candidates() -> tuple[Path, ...]:
    return service_registry_path(), bundled_registry_path()


def load_service_registry() -> dict[str, Any]:
    for path in _registry_candidates():
        if not path.is_file():
            continue
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        validate_service_registry(payload)
        return payload
    raise FileNotFoundError(
        "service registry not found: "
        + ", ".join(str(path) for path in _registry_candidates()))


def validate_service_registry(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise ValueError("service registry must be an object")
    if int(payload.get("schemaVersion", 0)) != 1:
        raise ValueError("unsupported service registry schemaVersion")
    services = payload.get("services")
    if not isinstance(services, list) or not services:
        raise ValueError("service registry services must be a non-empty list")
    seen = set()
    for service in services:
        if not isinstance(service, dict):
            raise ValueError("service registry item must be an object")
        missing = REQUIRED_SERVICE_KEYS.difference(service)
        if missing:
            raise ValueError(
                f"service registry item missing fields: {sorted(missing)}")
        key = str(service["key"])
        if key in seen:
            raise ValueError(f"duplicate service registry key: {key}")
        seen.add(key)


def monitor_defaults() -> list[dict[str, Any]]:
    result = []
    for service in load_service_registry()["services"]:
        monitor = service.get("monitor", {})
        item = {
            "key": service["key"],
            "exe": service["launcher"],
            "args": "",
            "name": service["name"],
            "delay": int(monitor.get("delaySeconds", 5)),
            "monitorAble": bool(monitor.get("enabled", True)),
        }
        heartbeat = service.get("heartbeat") or {}
        if heartbeat.get("port"):
            item["heartbeatHost"] = heartbeat.get("host", "127.0.0.1")
            item["heartbeatPort"] = int(heartbeat["port"])
            item["heartbeatTimeoutSeconds"] = int(
                heartbeat.get("timeoutSeconds", 200))
        process = service.get("process") or {}
        if process.get("pidFiles"):
            item["processPidFiles"] = list(process["pidFiles"])
        result.append(item)
    return result
