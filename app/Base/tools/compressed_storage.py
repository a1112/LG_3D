import json
import os
import uuid
from pathlib import Path

import numpy as np
from PIL import Image


def compressed_image_path(path: Path | str) -> Path:
    path = Path(path)
    if path.suffix.lower() == ".bmp":
        return path.with_suffix(".jpg")
    return path


def compressed_numpy_path(path: Path | str) -> Path:
    path = Path(path)
    if path.suffix.lower() == ".npy":
        return path.with_suffix(".npz")
    return path


def _temporary_output_path(path: Path) -> Path:
    return path.with_name(f".{path.stem}.{uuid.uuid4().hex}.tmp{path.suffix}")


def atomic_write_bytes(data: bytes, path: Path | str) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = _temporary_output_path(output_path)
    try:
        temporary_path.write_bytes(data)
        os.replace(temporary_path, output_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return output_path


def save_compressed_image(image: Image.Image,
                          path: Path | str,
                          quality: int = 95) -> Path:
    save_path = compressed_image_path(path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = _temporary_output_path(save_path)
    try:
        suffix = save_path.suffix.lower()
        if suffix == ".png":
            # PNG optimize performs an expensive full-image search and made
            # online 3D coils wait tens of seconds per derived image.
            image.save(temporary_path, compress_level=1, optimize=False)
        elif suffix in (".jpg", ".jpeg"):
            image.save(temporary_path, quality=quality, optimize=False)
        else:
            image.save(temporary_path)
        os.replace(temporary_path, save_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    original_path = Path(path)
    if original_path != save_path and original_path.exists():
        original_path.unlink()
    return save_path


def save_compressed_numpy(array: np.ndarray, path: Path | str) -> Path:
    save_path = compressed_numpy_path(path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = _temporary_output_path(save_path)
    try:
        np.savez_compressed(temporary_path, array=array)
        os.replace(temporary_path, save_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    original_path = Path(path)
    if original_path != save_path and original_path.exists():
        original_path.unlink()
    return save_path


def load_json_file(path: Path | str):
    path = Path(path)
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)
