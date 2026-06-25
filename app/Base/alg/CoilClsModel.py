import json
import time
from pathlib import Path, WindowsPath
from typing import Any, Optional

import numpy as np
import torch
from PIL import Image
from timm.data import resolve_data_config
from timm.data.transforms_factory import create_transform
from timm.models import create_model

from Base.CONFIG import get_file_url
from Base.utils.Log import logger


def _load_checkpoint(checkpoint_path: Optional[Path]) -> Optional[dict[str, Any]]:
    if checkpoint_path is None or not checkpoint_path.exists():
        return None
    try:
        checkpoint = torch.load(checkpoint_path, map_location="cpu")
        return checkpoint if isinstance(checkpoint, dict) else None
    except Exception as e:
        logger.warning("读取分类模型权重失败: %s", e)
        return None


def _unwrap_state_dict(checkpoint: Optional[dict[str, Any]]) -> dict[str, Any]:
    if isinstance(checkpoint, dict):
        for key in ("state_dict", "model", "model_state_dict"):
            value = checkpoint.get(key)
            if isinstance(value, dict):
                return value
    return checkpoint if isinstance(checkpoint, dict) else {}


def _infer_num_classes(checkpoint: Optional[dict[str, Any]]) -> Optional[int]:
    args = checkpoint.get("args") if isinstance(checkpoint, dict) else None
    if args is not None:
        num_classes = getattr(args, "num_classes", None)
        if isinstance(num_classes, int) and num_classes > 0:
            return num_classes

    state_dict = _unwrap_state_dict(checkpoint)
    for key, value in state_dict.items():
        if not hasattr(value, "shape") or len(value.shape) != 2:
            continue
        lower_key = key.lower()
        if lower_key.endswith(("classifier.weight", "fc.weight", "head.weight", "head.fc.weight")):
            return int(value.shape[0])
    return None


def _extract_names_from_checkpoint(checkpoint: Optional[dict[str, Any]]) -> list[str]:
    if not isinstance(checkpoint, dict):
        return []

    for key in ("names", "class_names", "labels", "classes"):
        value = checkpoint.get(key)
        if isinstance(value, dict):
            try:
                return [str(value[idx]) for idx in sorted(value)]
            except Exception as e:
                logger.debug("checkpoint class names mapping parse failed for %s: %s", key, e)
        if isinstance(value, (list, tuple)):
            return [str(item) for item in value]

    for key in ("idx_to_class", "class_to_idx"):
        value = checkpoint.get(key)
        if isinstance(value, dict) and value:
            try:
                if key == "idx_to_class":
                    normalized = {int(k): str(v) for k, v in value.items()}
                    return [normalized[idx] for idx in sorted(normalized)]
                normalized = {int(v): str(k) for k, v in value.items()}
                return [normalized[idx] for idx in sorted(normalized)]
            except Exception as e:
                logger.debug("checkpoint %s parse failed: %s", key, e)

    return []


class CoilClsModel:
    def __init__(self, model_name=None, checkpoint_path=None, in_chans=3, config=None):
        self.model_name = model_name
        self.checkpoint_path = checkpoint_path
        self.in_chans = in_chans
        if model_name is None and config is None:
            config = get_file_url(r"model/classifier/classifier.json")

        self.names: list[str] = []
        config_data = None
        if config is not None:
            config_path = Path(config)
            config_data = json.loads(config_path.read_text(encoding="utf-8"))
            self.model_name = config_data["model_name"]
            checkpoint_cfg = config_data["checkpoint_path"]
            checkpoint_path = Path(checkpoint_cfg)
            if not checkpoint_path.is_absolute():
                checkpoint_path = (config_path.parent / checkpoint_path).resolve()
            if not checkpoint_path.exists():
                checkpoint_path = Path(get_file_url(checkpoint_cfg))
            self.checkpoint_path = checkpoint_path
            self.in_chans = config_data["in_chans"]
            self.names = list(config_data.get("names", []))

        checkpoint = _load_checkpoint(Path(self.checkpoint_path) if self.checkpoint_path is not None else None)
        checkpoint_names = _extract_names_from_checkpoint(checkpoint)
        if checkpoint_names:
            self.names = checkpoint_names

        num_classes = _infer_num_classes(checkpoint) or (len(self.names) if self.names else None)
        if self.names and num_classes is not None and len(self.names) != num_classes:
            raise ValueError(f"分类名称数量({len(self.names)})与模型类别数({num_classes})不一致")

        self.model = create_model(
            self.model_name,
            checkpoint_path=self.checkpoint_path,
            num_classes=num_classes,
            in_chans=self.in_chans,
        )
        self.model.eval()

        self.device = "cpu"
        if torch.cuda.is_available():
            self.device = "cuda:0"
            self.model = self.model.cuda()

        self.config = resolve_data_config({}, model=self.model)
        if config_data is not None:
            if "input_size" in config_data:
                try:
                    self.config["input_size"] = tuple(config_data["input_size"])
                except Exception as e:
                    logger.error("classifier.json input_size 解析失败: %s", e)
            if "mean" in config_data:
                try:
                    self.config["mean"] = tuple(config_data["mean"])
                except Exception as e:
                    logger.error("classifier.json mean 解析失败: %s", e)
            if "std" in config_data:
                try:
                    self.config["std"] = tuple(config_data["std"])
                except Exception as e:
                    logger.error("classifier.json std 解析失败: %s", e)

        if self.in_chans == 1 and (config_data is None or "input_size" not in config_data):
            self.config["input_size"] = (1, 224, 224)
            self.config["mean"] = (0.485,)
            self.config["std"] = (0.229,)
        logger.debug(self.config)
        logger.info("分类模型类别顺序: %s", self.names)
        self.transform = create_transform(**self.config)

    def image_to_tensor(self, image):
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image)
        if self.in_chans == 1:
            return self.transform(image)
        return self.transform(image.convert("RGB"))

    def predict_image(self, image_list, bach_size=32):
        res_index, res_source, names = [], [], []
        image_cache = torch.Tensor().to(self.device)
        for index, img_ in list(enumerate(image_list)):
            if isinstance(img_, (str, WindowsPath)):
                try:
                    img_ = Image.open(img_)
                except (OSError, ValueError) as e:
                    logger.warning("load classifier image failed: %s", e)
                    continue
            tensor = self.image_to_tensor(img_)
            tensor = tensor.to(self.device)
            image_cache = torch.cat([image_cache, tensor[None]])
            if image_cache.shape[0] < bach_size and index < len(image_list) - 1:
                continue

            with torch.no_grad():
                pred_results_list = self.model(image_cache)
                for out in pred_results_list:
                    ls = list(torch.nn.functional.softmax(out, dim=0).cpu().numpy())
                    pred_index = ls.index(max(ls))
                    res_index.append(pred_index)
                    res_source.append(float(max(ls)))
                    names.append(self.names[pred_index] if pred_index < len(self.names) else str(pred_index))
            image_cache = torch.Tensor().to(self.device)
        return res_index, res_source, names


if __name__ == "__main__":
    st = time.time()
    ccm = CoilClsModel()

    r = ccm.predict_image([Image.open(r"E:\clfData\test\边部背景\92537_0.655604_14.jpg")] * 100)
    et = time.time()
    logger.info("classifier demo elapsed: %.3fs", et - st)
