import json
import os
from pathlib import Path
from threading import Lock, Thread
import time
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from configs import CONFIG
from configs.JoinConfig import JoinConfig
from JoinService.JoinWork import JoinWork
from utils.MultiprocessColorLogger import logger

app = FastAPI()

join_config = JoinConfig(CONFIG.JOIN_CONFIG_FILE)
join_work = JoinWork(join_config)
scanner_lock = Lock()
scanner_stats = {
    "enabled": True,
    "scanInterval": int(os.getenv("ALG_2D_AUTO_SCAN_INTERVAL", "10")),
    "scanLimit": int(os.getenv("ALG_2D_AUTO_SCAN_LIMIT", "20")),
    "maxQueueDepth": int(os.getenv("ALG_2D_AUTO_SCAN_MAX_QUEUE_DEPTH", "1")),
    "minImagesPerCamera": int(os.getenv("ALG_2D_MIN_IMAGES_PER_CAMERA", "2")),
    "maxCameraCountSkew": int(os.getenv("ALG_2D_MAX_CAMERA_COUNT_SKEW", "2")),
    "scanRunning": False,
    "lastScanStartTime": 0,
    "lastScanTime": 0,
    "lastScanError": "",
    "lastCandidates": [],
    "queued": [],
    "skippedProcessed": 0,
    "skippedIncomplete": 0,
    "skippedQueueFull": 0,
    "queueFailures": [],
}


class ClipConfigPayload(BaseModel):
    surface_key: str = Field(..., description="Surface key, e.g. S/L")
    mode: str = Field("fixed", description="fixed or dynamic")
    fixed: int = Field(200, ge=0)
    a: float = 3.0
    b: float = 220.0
    c: float = 2600.0
    offset: Optional[int] = None


class RejoinPayload(BaseModel):
    coil_id: int
    surface_key: Optional[str] = None


def _normalize_surface_key(key: str) -> str:
    key = (key or "").strip().upper()
    if key not in join_config.surfaces:
        raise HTTPException(status_code=400, detail=f"Unknown surface_key: {key}")
    return key


def _load_join_config(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_join_config(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def _apply_clip_config(surface_config, clip_config: dict) -> None:
    surface_config.clip_mode = clip_config.get("mode", "fixed")
    surface_config.clip_fixed = int(clip_config.get("fixed", 200))
    surface_config.clip_dynamic_a = float(clip_config.get("a", 3))
    surface_config.clip_dynamic_b = float(clip_config.get("b", 220))
    surface_config.clip_dynamic_c = float(clip_config.get("c", 2600))
    surface_config.clip_dynamic_offset = int(clip_config.get("offset", 40))


@app.post("/clip_config")
def set_clip_config(payload: ClipConfigPayload):
    surface_key = _normalize_surface_key(payload.surface_key)
    if payload.mode not in {"fixed", "dynamic"}:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {payload.mode}")
    config_path = Path(CONFIG.JOIN_CONFIG_FILE)
    data = _load_join_config(config_path)
    surfaces = data.get("surfaces", {})
    surface_cfg = surfaces.get(surface_key)
    if surface_cfg is None:
        raise HTTPException(status_code=400, detail=f"Missing surface config: {surface_key}")

    existing_clip = surface_cfg.get("clip_config", {})
    merged_clip = {
        "mode": payload.mode,
        "fixed": int(payload.fixed),
        "a": float(payload.a),
        "b": float(payload.b),
        "c": float(payload.c),
        "offset": existing_clip.get("offset", 40) if payload.offset is None else int(payload.offset),
    }
    surface_cfg["clip_config"] = merged_clip
    _save_join_config(config_path, data)

    join_config.config["surfaces"][surface_key]["clip_config"] = merged_clip
    _apply_clip_config(join_config.surfaces[surface_key], merged_clip)
    logger.info("Updated clip config %s: %s", surface_key, merged_clip)
    return {"status": "ok", "surface_key": surface_key, "clip_config": merged_clip}


def _enqueue(surface, coil_id: int) -> bool:
    try:
        surface.queue_in.put(coil_id, timeout=1)
        return True
    except Exception:
        return False


def _queue_depths() -> dict:
    depths = {"join": join_work.queue_in.qsize()}
    for key, surface in join_work.surface_dict.items():
        depths[key] = surface.queue_in.qsize()
    return depths


def _queue_has_capacity() -> bool:
    max_depth = int(scanner_stats["maxQueueDepth"])
    return max(_queue_depths().values() or [0]) < max_depth


def _surface_complete(surface_config, coil_id: int) -> bool:
    counts = []
    for camera_config in surface_config.camera_configs:
        folder = camera_config.get_folder(coil_id)
        if not folder.exists():
            return False
        try:
            count = sum(1 for entry in os.scandir(folder) if entry.is_file() and entry.name.lower().endswith(".jpg"))
        except OSError:
            return False
        if count < int(scanner_stats["minImagesPerCamera"]):
            return False
        counts.append(count)
    if counts and max(counts) - min(counts) > int(scanner_stats["maxCameraCountSkew"]):
        return False
    return True


def _surface_processed(surface_config, coil_id: int) -> bool:
    return surface_config.get_area_url(coil_id).exists()


def _source_coil_ids(limit: int) -> list[int]:
    coil_ids = set()
    for surface_config in join_config.surfaces.values():
        for camera_config in surface_config.camera_configs:
            base = camera_config.folder
            if not base.exists():
                continue
            ids = []
            with os.scandir(base) as entries:
                for entry in entries:
                    if entry.is_dir() and entry.name.isdigit():
                        ids.append(int(entry.name))
            coil_ids.update(sorted(ids, reverse=True)[:limit])
    return sorted(coil_ids, reverse=True)[:limit]


def _coil_needs_work(coil_id: int) -> tuple[bool, str]:
    incomplete = []
    missing_output = []
    for key, surface_config in join_config.surfaces.items():
        if not _surface_complete(surface_config, coil_id):
            incomplete.append(key)
            continue
        if not _surface_processed(surface_config, coil_id):
            missing_output.append(key)
    if missing_output:
        return True, ",".join(missing_output)
    if incomplete:
        return False, f"incomplete:{','.join(incomplete)}"
    return False, "processed"


def _scan_and_enqueue() -> None:
    with scanner_lock:
        if scanner_stats["scanRunning"]:
            return
        scanner_stats["scanRunning"] = True
        scanner_stats["lastScanStartTime"] = time.time()
        scanner_stats["lastScanError"] = ""

    scan_limit = int(scanner_stats["scanLimit"])
    try:
        candidates = _source_coil_ids(scan_limit)
        queued = []
        failures = []
        skipped_processed = 0
        skipped_incomplete = 0
        skipped_queue_full = 0
        for coil_id in candidates:
            if not _queue_has_capacity():
                skipped_queue_full += 1
                break
            needs_work, reason = _coil_needs_work(coil_id)
            if not needs_work:
                if reason == "processed":
                    skipped_processed += 1
                else:
                    skipped_incomplete += 1
                continue
            if _enqueue(join_work, coil_id):
                queued.append({"coil_id": coil_id, "reason": reason})
            else:
                failures.append(coil_id)
                break

        with scanner_lock:
            scanner_stats["lastScanTime"] = time.time()
            scanner_stats["lastCandidates"] = candidates[:20]
            scanner_stats["queued"] = queued[:20]
            scanner_stats["skippedProcessed"] = skipped_processed
            scanner_stats["skippedIncomplete"] = skipped_incomplete
            scanner_stats["skippedQueueFull"] = skipped_queue_full
            scanner_stats["queueFailures"] = failures[:20]
    except Exception as e:
        with scanner_lock:
            scanner_stats["lastScanError"] = str(e)
        raise
    finally:
        with scanner_lock:
            scanner_stats["scanRunning"] = False


def _auto_scan_loop() -> None:
    while scanner_stats["enabled"]:
        try:
            _scan_and_enqueue()
        except Exception as e:
            logger.error("2D auto scan failed: %s", e)
        time.sleep(max(int(scanner_stats["scanInterval"]), 2))


Thread(target=_auto_scan_loop, name="area-auto-scan", daemon=True).start()


@app.post("/area/rejoin")
def rejoin_area(payload: RejoinPayload):
    surface_keys = []
    if payload.surface_key:
        surface_keys.append(_normalize_surface_key(payload.surface_key))
    else:
        surface_keys = list(join_work.surface_dict.keys())

    queued = []
    failed = []
    for key in surface_keys:
        surface = join_work.surface_dict.get(key)
        if surface is None:
            failed.append(key)
            continue
        if _enqueue(surface, payload.coil_id):
            queued.append(key)
        else:
            failed.append(key)

    return {"status": "queued", "coil_id": payload.coil_id, "queued": queued, "failed": failed}


@app.get("/area/status")
def area_status():
    with scanner_lock:
        stats = dict(scanner_stats)
    return {
        "status": "ok",
        "scanner": stats,
        "joinQueueSize": join_work.queue_in.qsize(),
        "queueDepths": _queue_depths(),
        "surfaces": {
            key: {
                "queueSize": surface.queue_in.qsize(),
                "lastCoilId": surface.coil_id,
            }
            for key, surface in join_work.surface_dict.items()
        },
    }


@app.post("/area/scan")
def scan_area_once():
    _scan_and_enqueue()
    return area_status()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=6020)
