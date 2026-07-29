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
from .class_name_map import mapped_class_result, normalize_name_map


def _load_checkpoint(
        checkpoint_path: Optional[Path]) -> Optional[dict[str, Any]]:
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
        if lower_key.endswith(("classifier.weight", "fc.weight", "head.weight",
                               "head.fc.weight")):
            return int(value.shape[0])
    return None


def _extract_names_from_checkpoint(
        checkpoint: Optional[dict[str, Any]]) -> list[str]:
    if not isinstance(checkpoint, dict):
        return []

    for key in ("names", "class_names", "labels", "classes"):
        value = checkpoint.get(key)
        if isinstance(value, dict):
            try:
                return [str(value[idx]) for idx in sorted(value)]
            except Exception as e:
                logger.debug(
                    "checkpoint class names mapping parse failed for %s: %s",
                    key, e)
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

    def __init__(self,
                 model_name=None,
                 checkpoint_path=None,
                 in_chans=3,
                 config=None):
        self.model_name = model_name
        self.checkpoint_path = checkpoint_path
        self.in_chans = in_chans
        self.name_map: dict[str, str] = {}
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
                checkpoint_path = (config_path.parent /
                                   checkpoint_path).resolve()
            if not checkpoint_path.exists():
                checkpoint_path = Path(get_file_url(checkpoint_cfg))
            self.checkpoint_path = checkpoint_path
            self.in_chans = config_data["in_chans"]
            self.names = list(config_data.get("names", []))
            self.name_map = normalize_name_map(
                config_data.get("class_name_map",
                                config_data.get("name_map", {})))

        checkpoint = _load_checkpoint(
            Path(self.checkpoint_path) if self.
            checkpoint_path is not None else None)
        checkpoint_names = _extract_names_from_checkpoint(checkpoint)
        if checkpoint_names:
            self.names = checkpoint_names

        num_classes = _infer_num_classes(checkpoint) or (len(self.names) if
                                                         self.names else None)
        if self.names and num_classes is not None and len(
                self.names) != num_classes:
            raise ValueError(
                f"分类名称数量({len(self.names)})与模型类别数({num_classes})不一致")
        missing_map_targets = sorted({
            target
            for target in self.name_map.values() if target not in self.names
        })
        if missing_map_targets:
            logger.warning("分类类别映射目标不存在: %s", missing_map_targets)

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
                    self.config["input_size"] = tuple(
                        config_data["input_size"])
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

        if self.in_chans == 1 and (config_data is None
                                   or "input_size" not in config_data):
            self.config["input_size"] = (1, 224, 224)
            self.config["mean"] = (0.485, )
            self.config["std"] = (0.229, )
        logger.debug(self.config)
        logger.info("分类模型类别顺序: %s", self.names)
        if self.name_map:
            logger.info("分类模型类别映射: %s", self.name_map)
        self.transform = create_transform(**self.config)

    def image_to_tensor(self, image):
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image)
        if self.in_chans == 1:
            return self.transform(image)
        return self.transform(image.convert("RGB"))

    def predict_image(self, image_list, bach_size=32, deadline=None):
        res_index, res_source, names = [], [], []
        batch_size = max(int(bach_size), 1)
        for batch_start in range(0, len(image_list), batch_size):
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError("classifier preprocessing timeout")
            tensors = []
            for img_ in image_list[batch_start:batch_start + batch_size]:
                if isinstance(img_, (str, WindowsPath)):
                    try:
                        with Image.open(img_) as opened_image:
                            tensor = self.image_to_tensor(opened_image)
                    except (OSError, ValueError) as e:
                        logger.warning("load classifier image failed: %s", e)
                        continue
                else:
                    tensor = self.image_to_tensor(img_)
                tensors.append(tensor)
            if not tensors:
                continue
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError("classifier preprocessing timeout")

            image_cache = torch.stack(tensors).to(self.device,
                                                  non_blocking=True)
            with torch.inference_mode():
                pred_results_list = self.model(image_cache)
                for out in pred_results_list:
                    ls = list(
                        torch.nn.functional.softmax(out, dim=0).cpu().numpy())
                    pred_index = ls.index(max(ls))
                    if pred_index < len(self.names):
                        pred_name = self.names[pred_index]
                    else:
                        pred_name = str(pred_index)
                    pred_index, pred_name = mapped_class_result(
                        pred_index, pred_name, self.names, self.name_map)
                    res_index.append(pred_index)
                    res_source.append(float(max(ls)))
                    names.append(pred_name)
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError("classifier inference timeout")
        return res_index, res_source, names


if __name__ == "__main__":
    st = time.time()
    ccm = CoilClsModel()

    r = ccm.predict_image(
        [Image.open(r"E:\clfData\test\边部背景\92537_0.655604_14.jpg")] * 100)
    et = time.time()
    logger.info("classifier demo elapsed: %.3fs", et - st)
