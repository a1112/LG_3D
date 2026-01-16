import json
from pathlib import Path
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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=6020)
