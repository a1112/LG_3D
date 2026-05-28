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


def save_compressed_image(image: Image.Image, path: Path | str, quality: int = 95) -> Path:
    save_path = compressed_image_path(path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(save_path, quality=quality, optimize=True)
    original_path = Path(path)
    if original_path != save_path and original_path.exists():
        original_path.unlink()
    return save_path


def save_compressed_numpy(array: np.ndarray, path: Path | str) -> Path:
    save_path = compressed_numpy_path(path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(save_path, array=array)
    original_path = Path(path)
    if original_path != save_path and original_path.exists():
        original_path.unlink()
    return save_path
