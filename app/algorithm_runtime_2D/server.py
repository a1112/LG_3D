import json
import os
import sys
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event, Lock, Thread
import time
from typing import Optional

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from Base.utils.watchdog_bootstrap import maybe_exec_watchdog

maybe_exec_watchdog(
    __name__,
    Path(__file__).with_name("watchdog.py"),
    child_environment="LG3D_ALGORITHM_2D_WATCHDOG_CHILD",
    disable_environment="LG3D_ALGORITHM_2D_DISABLE_AUTO_WATCHDOG",
    service_name="LG3D 2D algorithm",
)

_runtime_lock = None
if __name__ == "__main__":
    from Base.utils.Singleton import SingletonLock

    _runtime_lock = SingletonLock("algorithm_runtime_2d")
    if not _runtime_lock.acquire():
        raise SystemExit("2D algorithm runtime is already running")

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from algorithm_runtime_2D.runtime_heartbeat import runtime_heartbeat

runtime_heartbeat.start()
startup_activity = runtime_heartbeat.begin_activity(
    "2d_runtime_initialization"
)

from algorithm_runtime_2D.configs import CONFIG
from algorithm_runtime_2D.configs.JoinConfig import JoinConfig
from algorithm_runtime_2D.JoinService.JoinWork import JoinWork
from algorithm_runtime_2D.JoinService.RecoveryQueue import (merge_history_candidates,
                                                             prune_retry_state,
                                                             take_next_history_candidate)
from algorithm_runtime_2D.utils.MultiprocessColorLogger import logger

app = FastAPI()

MAX_RECOVERY_COILS = 500
HISTORY_CHECKS_PER_SCAN = 25


def _bounded_int_env(name: str, default: int, *, min_value: int = 1, max_value: int | None = None) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        value = int(raw_value)
    except ValueError:
        logger.warning("invalid %s=%s, use %s", name, raw_value, default)
        value = default

    value = max(value, min_value)
    if max_value is not None and value > max_value:
        logger.warning("%s=%s exceeds max %s, clamp to %s", name, value, max_value, max_value)
        value = max_value
    return value


try:
    join_config = JoinConfig(CONFIG.JOIN_CONFIG_FILE)
    join_work = JoinWork(join_config)
finally:
    runtime_heartbeat.end_activity(startup_activity)
manual_result_executors = {
    key: ThreadPoolExecutor(
        max_workers=1,
        thread_name_prefix=f"area-rejoin-result-{key}",
    )
    for key in join_work.surface_dict
}
scanner_lock = Lock()
scanner_stop_event = Event()
history_candidates = deque(maxlen=MAX_RECOVERY_COILS)
history_known_ids = set()
retry_state = {}
scanner_stats = {
    "enabled": True,
    "scanDirection": "new_to_old",
    "scanInterval": _bounded_int_env("ALG_2D_AUTO_SCAN_INTERVAL", 10, min_value=2),
    "scanLimit": _bounded_int_env("ALG_2D_AUTO_SCAN_LIMIT", MAX_RECOVERY_COILS, max_value=MAX_RECOVERY_COILS),
    "scanLimitCap": MAX_RECOVERY_COILS,
    "liveScanLimit": _bounded_int_env("ALG_2D_LIVE_SCAN_LIMIT", 5, max_value=MAX_RECOVERY_COILS),
    "maxQueueDepth": _bounded_int_env("ALG_2D_AUTO_SCAN_MAX_QUEUE_DEPTH", 1),
    "minImagesPerCamera": _bounded_int_env("ALG_2D_MIN_IMAGES_PER_CAMERA", 2),
    "maxCameraCountSkew": _bounded_int_env("ALG_2D_MAX_CAMERA_COUNT_SKEW", 2, min_value=0),
    "sourceQuietSeconds": _bounded_int_env("ALG_2D_SOURCE_QUIET_SECONDS", 10, min_value=1),
    "scanRunning": False,
    "historyScanDone": False,
    "historyPending": 0,
    "lastScanMode": "",
    "lastScanStartTime": 0,
    "lastScanTime": 0,
    "lastScanError": "",
    "candidateCount": 0,
    "lastCandidates": [],
    "queued": [],
    "skippedProcessed": 0,
    "skippedInFlight": 0,
    "skippedBackoff": 0,
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


@app.get("/health")
def health():
    state = runtime_heartbeat.snapshot()
    return {
        "ok": state["ok"],
        "service": "LG3D_ALGORITHM_2D",
        "heartbeat": state,
    }


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
    if hasattr(surface, "add_work"):
        return bool(surface.add_work(coil_id, timeout=1))
    try:
        surface.queue_in.put(coil_id, timeout=1)
        return True
    except Exception as e:
        logger.warning("2D enqueue failed: target=%s coil_id=%s error=%s",
                       type(surface).__name__,
                       coil_id,
                       e)
        return False


def _consume_manual_surface_result(surface, ticket) -> None:
    try:
        surface.get(timeout=300, expected_ticket=ticket)
    except Exception as e:
        logger.exception(
            "2D manual surface result consumer failed: surface=%s work_id=%s error=%s",
            getattr(surface, "key", type(surface).__name__),
            getattr(ticket, "work_id", None),
            e,
        )


def _queue_depths() -> dict:
    depths = {
        "joinQueued": join_work.queue_in.qsize(),
        "joinPending": join_work.pending_count(),
        "pipelinePending": join_work.pending_work_count(),
    }
    for key, surface in join_work.surface_dict.items():
        depths[key] = surface.pending_count()
        depths[f"{key}Save"] = surface.save_wolk.pending_count()
    return depths


def _queue_has_capacity() -> bool:
    max_depth = int(scanner_stats["maxQueueDepth"])
    return join_work.pending_work_count() < max_depth


def _surface_complete(surface_config, coil_id: int) -> bool:
    return surface_config.source_complete(
        coil_id,
        min_images_per_camera=int(scanner_stats["minImagesPerCamera"]),
        max_camera_count_skew=int(scanner_stats["maxCameraCountSkew"]),
        quiet_seconds=float(scanner_stats["sourceQuietSeconds"]),
    )


def _surface_processed(surface_config, coil_id: int) -> bool:
    return surface_config.area_output_complete(coil_id)


def _source_coil_ids(limit: int) -> list[int]:
    limit = max(min(int(limit), MAX_RECOVERY_COILS), 1)
    return join_config.get_source_coil_ids(limit)


def _init_history_candidates() -> None:
    global history_candidates, history_known_ids
    with scanner_lock:
        if scanner_stats["historyScanDone"]:
            return

    candidates = _source_coil_ids(int(scanner_stats["scanLimit"]))
    with scanner_lock:
        history_candidates = deque(candidates, maxlen=MAX_RECOVERY_COILS)
        history_known_ids = set(candidates)
        prune_retry_state(retry_state, history_known_ids,
                          MAX_RECOVERY_COILS)
        scanner_stats["historyScanDone"] = True
        scanner_stats["historyPending"] = len(history_candidates)
        scanner_stats["candidateCount"] = len(candidates)
        scanner_stats["lastCandidates"] = candidates[:20]
        scanner_stats["lastScanMode"] = "history_init"
    logger.info("2D startup history scan done: candidates=%s", len(candidates))


def _merge_history_candidates(candidates: list[int]) -> None:
    with scanner_lock:
        new_candidates = merge_history_candidates(
            history_candidates,
            history_known_ids,
            candidates,
            max_candidates=MAX_RECOVERY_COILS,
        )
        prune_retry_state(retry_state, history_known_ids,
                          MAX_RECOVERY_COILS)
    if new_candidates:
        logger.info("2D history discovered new coils: count=%s newest=%s", len(new_candidates), new_candidates[:5])


def _next_history_candidate() -> int | None:
    return take_next_history_candidate(
        history_candidates,
        _coil_needs_work,
        HISTORY_CHECKS_PER_SCAN,
    )


def _coil_needs_work(coil_id: int) -> tuple[bool, str]:
    if join_work.has_pending_work(coil_id):
        return False, "inflight"

    incomplete = []
    missing_output = []
    for key, surface_config in join_config.surfaces.items():
        if _surface_processed(surface_config, coil_id):
            continue
        if _surface_complete(surface_config, coil_id):
            missing_output.append(key)
        else:
            incomplete.append(key)
    if missing_output:
        state = retry_state.get(coil_id)
        if state is not None and time.time() < state["nextRetryTime"]:
            return False, "backoff"
        return True, ",".join(missing_output)
    if incomplete:
        return False, f"incomplete:{','.join(incomplete)}"
    retry_state.pop(coil_id, None)
    return False, "processed"


def _enqueue_candidates(candidates: list[int], mode: str):
    queued = []
    failures = []
    skipped_processed = 0
    skipped_inflight = 0
    skipped_backoff = 0
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
            elif reason == "inflight":
                skipped_inflight += 1
            elif reason == "backoff":
                skipped_backoff += 1
            else:
                skipped_incomplete += 1
            continue
        if _enqueue(join_work, coil_id):
            queued.append({"coil_id": coil_id, "reason": reason, "mode": mode})
            state = retry_state.setdefault(coil_id, {"attempts": 0, "nextRetryTime": 0.0})
            state["attempts"] += 1
            retry_delay = min(
                int(scanner_stats["scanInterval"]) * (2 ** max(state["attempts"] - 1, 0)),
                300,
            )
            state["nextRetryTime"] = time.time() + retry_delay
        else:
            failures.append(coil_id)
            break
    return (
        queued,
        failures,
        skipped_processed,
        skipped_inflight,
        skipped_backoff,
        skipped_incomplete,
        skipped_queue_full,
    )


def _scan_and_enqueue(mode: str = "live") -> None:
    with scanner_lock:
        if scanner_stats["scanRunning"]:
            return
        scanner_stats["scanRunning"] = True
        scanner_stats["lastScanStartTime"] = time.time()
        scanner_stats["lastScanError"] = ""

    try:
        if mode == "history":
            if not scanner_stats["historyScanDone"]:
                _init_history_candidates()
            candidates = []
            history_candidate = _next_history_candidate()
            if history_candidate is not None:
                candidates.append(history_candidate)
            scan_result = _enqueue_candidates(candidates, "history")
        else:
            all_candidates = _source_coil_ids(int(scanner_stats["scanLimit"]))
            _merge_history_candidates(all_candidates)
            candidates = all_candidates[:int(scanner_stats["liveScanLimit"])]
            scan_result = _enqueue_candidates(candidates, "live")

        (
            queued,
            failures,
            skipped_processed,
            skipped_inflight,
            skipped_backoff,
            skipped_incomplete,
            skipped_queue_full,
        ) = scan_result

        with scanner_lock:
            scanner_stats["lastScanTime"] = time.time()
            scanner_stats["lastScanMode"] = mode
            scanner_stats["candidateCount"] = len(candidates)
            scanner_stats["lastCandidates"] = candidates[:20]
            scanner_stats["queued"] = queued[:20]
            scanner_stats["skippedProcessed"] = skipped_processed
            scanner_stats["skippedInFlight"] = skipped_inflight
            scanner_stats["skippedBackoff"] = skipped_backoff
            scanner_stats["skippedIncomplete"] = skipped_incomplete
            scanner_stats["skippedQueueFull"] = skipped_queue_full
            scanner_stats["queueFailures"] = failures[:20]
            scanner_stats["historyPending"] = len(history_candidates)
    except Exception as e:
        with scanner_lock:
            scanner_stats["lastScanError"] = str(e)
        raise
    finally:
        with scanner_lock:
            scanner_stats["scanRunning"] = False


def _auto_scan_loop() -> None:
    try:
        _init_history_candidates()
    except Exception as e:
        logger.exception("2D startup history scan failed: %s", e)
    while scanner_stats["enabled"]:
        try:
            _scan_and_enqueue("live")
            if _queue_has_capacity():
                _scan_and_enqueue("history")
        except Exception as e:
            logger.exception("2D auto scan failed: %s", e)
        scanner_stop_event.wait(max(int(scanner_stats["scanInterval"]), 2))


scanner_thread = Thread(target=_auto_scan_loop, name="area-auto-scan", daemon=True)
scanner_thread.start()


@app.on_event("shutdown")
def _shutdown_area_workers() -> None:
    scanner_stats["enabled"] = False
    scanner_stop_event.set()
    scanner_thread.join(timeout=2)
    join_work.stop(timeout=10)
    for executor in manual_result_executors.values():
        executor.shutdown(wait=False, cancel_futures=True)
    runtime_heartbeat.stop()


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
        ticket = surface.add_work(payload.coil_id, timeout=1)
        if ticket:
            try:
                manual_result_executors[key].submit(
                    _consume_manual_surface_result,
                    surface,
                    ticket,
                )
                queued.append(key)
            except RuntimeError as e:
                logger.warning(
                    "2D manual result consumer unavailable: surface=%s coil_id=%s error=%s",
                    key,
                    payload.coil_id,
                    e,
                )
                failed.append(key)
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
        "pendingCoilIds": sorted(join_work.pending_coil_ids()),
        "queueDepths": _queue_depths(),
        "surfaces": {
            key: {
                "queueSize": surface.queue_in.qsize(),
                "pendingCount": surface.pending_count(),
                "activeCoilId": surface.active_work_id,
                "savePendingCount": surface.save_wolk.pending_count(),
            }
            for key, surface in join_work.surface_dict.items()
        },
    }


@app.post("/area/scan")
def scan_area_once():
    _scan_and_enqueue()
    return area_status()


if __name__ == "__main__":
    try:
        uvicorn.run(app, host="0.0.0.0", port=6020, log_config=None)
    finally:
        if _runtime_lock is not None:
            _runtime_lock.release()
