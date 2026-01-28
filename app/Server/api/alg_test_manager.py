import asyncio
import json
import logging
import shutil
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Dict, List, Optional, Sequence

import cv2
from fastapi import HTTPException, WebSocket, WebSocketDisconnect
from PIL import Image
from ultralytics import YOLO

from Base.CONFIG import base_config_folder
from Base.alg.CoilClsModel import CoilClsModel

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
IOU_THRESHOLD = 0.5
MODEL_FOLDER = (Path(base_config_folder) / "model").resolve()
CLASSIFIER_FOLDER = (MODEL_FOLDER / "classifier").resolve()


def _sanitize_folder_name(text: str) -> str:
    if not text:
        return "empty"
    safe_chars = []
    for ch in text:
        safe_chars.append(ch if ch.isalnum() or ch in ("-", "_") else "_")
    name = "".join(safe_chars).strip("_")
    return name or "empty"


def _list_image_files(target: Path) -> List[Path]:
    files: List[Path] = []
    for path in target.rglob("*"):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            files.append(path)
    return sorted(files)


def _reserve_path(path: Path) -> Path:
    if not path.exists():
        return path
    index = 1
    while True:
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def _save_pascal_voc_xml(path: Path, image_name: str, width: int, height: int, boxes: Sequence[dict]) -> None:
    from xml.etree.ElementTree import Element, SubElement, ElementTree

    annotation = Element("annotation")
    SubElement(annotation, "folder").text = path.parent.name
    SubElement(annotation, "filename").text = image_name
    source = SubElement(annotation, "source")
    SubElement(source, "database").text = "Unknown"
    size = SubElement(annotation, "size")
    SubElement(size, "width").text = str(width)
    SubElement(size, "height").text = str(height)
    SubElement(size, "depth").text = "3"
    SubElement(annotation, "segmented").text = "0"

    for box in boxes:
        obj = SubElement(annotation, "object")
        SubElement(obj, "name").text = box["label"]
        SubElement(obj, "pose").text = "Unspecified"
        SubElement(obj, "truncated").text = "0"
        SubElement(obj, "difficult").text = "0"
        bndbox = SubElement(obj, "bndbox")
        xmin, ymin, xmax, ymax = box["bbox"]
        SubElement(bndbox, "xmin").text = str(int(xmin))
        SubElement(bndbox, "ymin").text = str(int(ymin))
        SubElement(bndbox, "xmax").text = str(int(xmax))
        SubElement(bndbox, "ymax").text = str(int(ymax))

    ElementTree(annotation).write(path, encoding="utf-8")


def _bbox_iou(a: Sequence[float], b: Sequence[float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    if inter_area <= 0:
        return 0.0
    area_a = max(0.0, (ax2 - ax1)) * max(0.0, (ay2 - ay1))
    area_b = max(0.0, (bx2 - bx1)) * max(0.0, (by2 - by1))
    union = area_a + area_b - inter_area
    if union <= 0:
        return 0.0
    return inter_area / union


def _analyze_boxes(boxes: Sequence[dict], threshold: float) -> dict:
    labels = [box["label"] for box in boxes]
    unique_labels = sorted(set(labels))
    combo = "_".join(unique_labels) if unique_labels else "empty"
    low_conf = any(box["conf"] < threshold for box in boxes)
    overlap_same = set()
    overlap_diff = set()
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            iou = _bbox_iou(boxes[i]["bbox"], boxes[j]["bbox"])
            if iou < IOU_THRESHOLD:
                continue
            if boxes[i]["label"] == boxes[j]["label"]:
                overlap_same.add(boxes[i]["label"])
            else:
                diff = "_".join(sorted({boxes[i]["label"], boxes[j]["label"]}))
                overlap_diff.add(diff)
    return {
        "combo": combo or "empty",
        "low_conf": low_conf,
        "overlap_same": overlap_same,
        "overlap_diff": overlap_diff,
        "has_boxes": len(boxes) > 0,
    }


def _generate_labelme_payload(result, threshold: float, image_path: Path):
    masks = getattr(result, "masks", None)
    if not masks:
        return None
    shapes = []
    xy_list = masks.xy
    for idx, box in enumerate(result.boxes):
        conf = float(box.conf[0].item())
        if conf < threshold:
            continue
        pts = xy_list[idx]
        if pts is None:
            continue
        label_idx = int(box.cls[0].item())
        label = result.names.get(label_idx, str(label_idx))
        shapes.append({
            "label": label,
            "points": [[float(pt[0]), float(pt[1])] for pt in pts],
            "group_id": None,
            "shape_type": "polygon",
            "flags": {}
        })
    if not shapes:
        return None
    image_width = image_height = 0
    if hasattr(result, "orig_shape") and result.orig_shape:
        image_height, image_width = result.orig_shape[:2]
    if not image_width or not image_height:
        arr = cv2.imread(str(image_path))
        if arr is not None:
            image_height, image_width = arr.shape[:2]
    return {
        "version": "5.2.1",
        "flags": {},
        "shapes": shapes,
        "imagePath": image_path.name,
        "imageData": None,
        "imageHeight": image_height,
        "imageWidth": image_width
    }


@dataclass
class AlgModelEntry:
    name: str
    path: Path
    type: str  # detector / segment / classifier

    def to_dict(self) -> dict:
        display = self.name
        if self.type == "segment":
            display = f"分割 · {self.name}"
        elif self.type == "classifier":
            display = f"分类器 · {self.name}"
        else:
            display = f"检测 · {self.name}"
        return {
            "name": self.name,
            "type": self.type,
            "display_name": display
        }


@dataclass
class AlgTestJob:
    id: str
    model: AlgModelEntry
    target: Path
    output: Path
    threshold: float
    mode: str
    options: Dict[str, bool]
    manager: "AlgTestManager"
    total: int = 0
    processed: int = 0
    errors: int = 0
    started_at: float = field(default_factory=time.monotonic)
    stop_event: Event = field(default_factory=Event)
    running: bool = True
    summary: Dict[str, int] = field(default_factory=lambda: {
        "normal": 0,
        "abnormal": 0,
        "skipped": 0,
        "empty": 0,
    })
    status: str = "初始化"

    def should_classify(self) -> bool:
        return bool(self.options.get("classify_save", True))

    def should_save_label(self) -> bool:
        if self.model.type == "classifier":
            return False
        return bool(self.options.get("save_label", False))

    def priority_mode(self) -> bool:
        return bool(self.options.get("prioritize", False))

    def image_mode(self) -> str:
        return "move" if self.mode == "move" else "copy"

    def eta_seconds(self) -> Optional[float]:
        elapsed = max(0.0001, time.monotonic() - self.started_at)
        speed = self.processed / elapsed if elapsed > 0 else 0.0
        if speed <= 0:
            return None
        remaining = max(0, self.total - self.processed)
        return remaining / speed if speed > 0 else None

    def current_speed(self) -> float:
        elapsed = max(0.0001, time.monotonic() - self.started_at)
        return self.processed / elapsed if elapsed > 0 else 0.0

    def build_payload(self, message: str = "", finished: bool = False) -> dict:
        eta = self.eta_seconds()
        return {
            "task_id": self.id,
            "status": self.status,
            "done": self.processed,
            "total": self.total,
            "speed": round(self.current_speed(), 4),
            "eta": eta,
            "errors": self.errors,
            "message": message,
            "finished": finished,
            "summary": self.summary,
        }


class AlgTestManager:
    def __init__(self) -> None:
        self._job_lock = Lock()
        self._current_job: Optional[AlgTestJob] = None
        self._listeners: Dict[int, Dict[str, object]] = {}
        self._listeners_lock = Lock()
        self._last_payload: dict = {"task_id": None, "status": "idle"}
        self._models: Dict[str, AlgModelEntry] = {}

    # ------------- models -------------
    def _guess_model_type(self, path: Path) -> str:
        lower = path.stem.lower()
        suffix = path.suffix.lower()
        if suffix == ".json":
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return "detector"
            if isinstance(data, dict) and "model_name" in data and "checkpoint_path" in data:
                return "classifier"
        if "seg" in lower or "mask" in lower:
            return "segment"
        return "detector"

    def _refresh_models(self) -> None:
        models: Dict[str, AlgModelEntry] = {}

        # 确保模型文件夹存在
        MODEL_FOLDER.mkdir(parents=True, exist_ok=True)
        CLASSIFIER_FOLDER.mkdir(parents=True, exist_ok=True)

        logger.info(f"扫描模型文件夹: {MODEL_FOLDER}")
        if MODEL_FOLDER.is_dir():
            all_files = list(MODEL_FOLDER.iterdir())
            logger.info(f"找到 {len(all_files)} 个文件/文件夹")
            for path in all_files:
                if not path.is_file():
                    logger.debug(f"跳过 (非文件): {path.name}")
                    continue
                suffix = path.suffix.lower()
                if suffix not in {".pt", ".onnx"}:
                    logger.debug(f"跳过 (不支持的后缀 {suffix}): {path.name}")
                    continue
                model_type = self._guess_model_type(path)
                models[path.name] = AlgModelEntry(name=path.name, path=path, type=model_type)
                logger.info(f"添加模型: {path.name} (类型: {model_type})")
        else:
            logger.warning(f"模型文件夹不存在: {MODEL_FOLDER}")

        logger.info(f"扫描分类器文件夹: {CLASSIFIER_FOLDER}")
        if CLASSIFIER_FOLDER.is_dir():
            for path in CLASSIFIER_FOLDER.iterdir():
                if not path.is_file():
                    continue
                suffix = path.suffix.lower()
                if suffix != ".json":
                    continue
                model_type = self._guess_model_type(path)
                if model_type != "classifier":
                    continue
                models[path.name] = AlgModelEntry(name=path.name, path=path, type=model_type)
                logger.info(f"添加分类器: {path.name}")

        logger.info(f"共找到 {len(models)} 个模型")
        self._models = models

    def list_models(self) -> List[dict]:
        self._refresh_models()
        return [entry.to_dict() for entry in sorted(self._models.values(), key=lambda e: (e.type, e.name))]

    def _resolve_model(self, name: str) -> AlgModelEntry:
        if name not in self._models:
            self._refresh_models()
        entry = self._models.get(name)
        if not entry:
            raise HTTPException(status_code=400, detail=f"model not found: {name}")
        if not entry.path.exists():
            raise HTTPException(status_code=400, detail=f"模型文件不存在: {entry.path}")
        return entry

    # ------------- websocket -------------
    async def handle_websocket(self, websocket: WebSocket) -> None:
        await websocket.accept()
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_running_loop()
        listener_id = id(websocket)
        with self._listeners_lock:
            self._listeners[listener_id] = {
                "websocket": websocket,
                "queue": queue,
                "loop": loop,
            }
        if self._last_payload:
            await queue.put(self._last_payload)
        try:
            while True:
                payload = await queue.get()
                await websocket.send_text(json.dumps(payload, ensure_ascii=False))
        except WebSocketDisconnect:
            pass
        finally:
            with self._listeners_lock:
                self._listeners.pop(listener_id, None)

    def _broadcast(self, payload: dict) -> None:
        self._last_payload = payload
        with self._listeners_lock:
            listeners = list(self._listeners.values())
        for listener in listeners:
            loop: asyncio.AbstractEventLoop = listener["loop"]
            queue: asyncio.Queue = listener["queue"]
            loop.call_soon_threadsafe(queue.put_nowait, payload)

    # ------------- helpers -------------
    def _resolve_dir(self, raw: str, label: str, must_exist: bool = False) -> Path:
        if not raw:
            raise HTTPException(status_code=400, detail=f"{label}不能为空")
        path = Path(raw).expanduser().resolve()
        if must_exist:
            if not path.is_dir():
                raise HTTPException(status_code=400, detail=f"{label}路径不存在: {raw}")
            return path
        path.mkdir(parents=True, exist_ok=True)
        return path

    # ------------- task control -------------
    def start_job(self, payload: dict) -> dict:
        with self._job_lock:
            if self._current_job and self._current_job.running:
                raise HTTPException(status_code=400, detail="已有算法测试任务在执行")

            model_name = payload.get("model")
            target = payload.get("target")
            output = payload.get("output")
            if not model_name or not isinstance(model_name, str):
                raise HTTPException(status_code=400, detail="model 必填")
            if not target:
                raise HTTPException(status_code=400, detail="target 必填")
            if not output:
                raise HTTPException(status_code=400, detail="output 必填")

            threshold = float(payload.get("threshold", 0.4))
            threshold = max(0.01, min(0.99, threshold))
            mode = payload.get("mode", "copy")
            options = payload.get("options") or {}

            model = self._resolve_model(model_name)
            target_path = self._resolve_dir(target, "目标", must_exist=True)
            output_path = self._resolve_dir(output, "输出")

            job = AlgTestJob(
                id=uuid.uuid4().hex,
                model=model,
                target=target_path,
                output=output_path,
                threshold=threshold,
                mode=mode,
                options={
                    "classify_save": bool(options.get("classify_save", True)),
                    "save_label": bool(options.get("save_label", False)),
                    "prioritize": bool(options.get("prioritize", False)),
                },
                manager=self,
            )
            self._current_job = job
            Thread(target=self._run_job, args=(job,), daemon=True).start()
            self._broadcast(job.build_payload("任务已启动"))
            return {"ok": True, "task_id": job.id}

    def stop_job(self, task_id: Optional[str]) -> dict:
        with self._job_lock:
            job = self._current_job
            if not job or not job.running:
                return {"ok": True, "message": "当前无任务"}
            if task_id and job.id != task_id:
                raise HTTPException(status_code=400, detail="任务 ID 不匹配")
            job.stop_event.set()
            return {"ok": True, "message": "停止指令已发送"}

    def _finish_job(self, job: AlgTestJob, message: str, finished: bool = True) -> None:
        job.running = False
        payload = job.build_payload(message, finished=finished)
        self._broadcast(payload)
        with self._job_lock:
            if self._current_job is job:
                self._current_job = None

    # ------------- processing -------------
    def _run_job(self, job: AlgTestJob) -> None:
        image_paths = _list_image_files(job.target)
        job.total = len(image_paths)
        if not image_paths:
            self._finish_job(job, "未找到可测试图片", finished=True)
            return

        self._broadcast(job.build_payload(f"共 {job.total} 张，准备加载模型"))

        try:
            if job.model.type == "classifier":
                model_instance = CoilClsModel(config=str(job.model.path))
            else:
                model_instance = YOLO(str(job.model.path))
        except Exception as exc:
            self._finish_job(job, f"模型加载失败: {exc}", finished=True)
            return

        job.status = "运行中"
        self._broadcast(job.build_payload("模型加载完成，开始遍历图片"))

        for index, image_path in enumerate(image_paths, 1):
            if job.stop_event.is_set():
                job.status = "已停止"
                self._finish_job(job, "任务已停止", finished=True)
                return

            message = ""
            try:
                if job.model.type == "classifier":
                    message = self._process_classification(job, model_instance, image_path)
                else:
                    message = self._process_detection(job, model_instance, image_path)
            except Exception as exc:  # pylint: disable=broad-except
                job.errors += 1
                message = f"{image_path.name} 处理失败: {exc}"

            job.processed = index
            self._broadcast(job.build_payload(message))

        job.status = "完成"
        self._finish_job(job, f"处理完成，共 {job.total} 张", finished=True)

    def _process_classification(self, job: AlgTestJob, model: CoilClsModel, image_path: Path) -> str:
        with Image.open(image_path) as img:
            preds, confs, names = model.predict_image([img], bach_size=1)
        if not preds:
            label = ""
            confidence = 0.0
        else:
            label = names[0]
            confidence = float(confs[0])

        combo = label or "empty"
        classification = "normal"
        reason = "classified"
        if not label:
            job.summary["empty"] += 1
            reason = "empty"
        elif confidence < job.threshold:
            classification = "abnormal"
            reason = "low_confidence"

        if classification == "abnormal":
            job.summary["abnormal"] += 1
        else:
            job.summary["normal"] += 1

        if job.priority_mode() and classification == "normal":
            job.summary["skipped"] += 1
            return f"{image_path.name} 正常(仅检测)"

        base_dir = job.output / classification
        sub_map = {
            "empty": "empty",
            "low_confidence": "low_confidence",
            "classified": "classified",
        }
        dest_dir = base_dir / sub_map[reason]
        if job.should_classify() and label:
            dest_dir = dest_dir / _sanitize_folder_name(label)
        dest_dir.mkdir(parents=True, exist_ok=True)

        dest_path = _reserve_path(dest_dir / image_path.name)
        if job.image_mode() == "move":
            shutil.move(str(image_path), dest_path)
        else:
            shutil.copy2(str(image_path), dest_path)

        return f"{image_path.name} -> {classification}/{sub_map[reason]} [{combo}]"

    def _process_detection(self, job: AlgTestJob, model: YOLO, image_path: Path) -> str:
        results = model(str(image_path))
        if not results:
            raise RuntimeError("模型无返回结果")
        result = results[0]
        boxes = []
        for box in result.boxes:
            xyxy = box.xyxy[0].cpu().numpy().tolist()
            label_idx = int(box.cls[0].item())
            label = result.names.get(label_idx, str(label_idx))
            boxes.append({
                "label": label,
                "conf": float(box.conf[0].item()),
                "bbox": [float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])],
            })
        analysis = _analyze_boxes(boxes, job.threshold)
        return self._handle_detection(job, image_path, result, boxes, analysis)

    def _handle_detection(self, job: AlgTestJob, image_path: Path, result, boxes: List[dict], analysis: dict) -> str:
        combo = analysis["combo"]
        classification = "normal"
        reason = "classified"

        if not analysis["has_boxes"]:
            job.summary["empty"] += 1
            reason = "empty"
        elif analysis["low_conf"]:
            classification = "abnormal"
            reason = "low_confidence"
        elif analysis["overlap_diff"]:
            classification = "abnormal"
            reason = "overlap_diff"
        elif analysis["overlap_same"]:
            classification = "abnormal"
            reason = "overlap_same"

        if classification == "abnormal":
            job.summary["abnormal"] += 1
        else:
            job.summary["normal"] += 1

        if job.priority_mode() and classification == "normal":
            job.summary["skipped"] += 1
            return f"{image_path.name} 正常(仅检测)"

        sub_map = {
            "empty": "empty",
            "low_confidence": "low_confidence",
            "overlap_same": "overlap_same",
            "overlap_diff": "overlap_diff",
            "classified": "classified",
        }
        base_dir = job.output / classification
        dest_dir = base_dir / sub_map[reason]
        if job.should_classify() and combo and combo != "empty":
            dest_dir = dest_dir / _sanitize_folder_name(combo)
        dest_dir.mkdir(parents=True, exist_ok=True)

        dest_path = _reserve_path(dest_dir / image_path.name)
        if job.image_mode() == "move":
            shutil.move(str(image_path), dest_path)
        else:
            shutil.copy2(str(image_path), dest_path)

        if job.should_save_label() and boxes:
            height = width = 0
            if hasattr(result, "orig_shape") and result.orig_shape:
                height, width = result.orig_shape[:2]
            if not width or not height:
                arr = cv2.imread(str(dest_path))
                if arr is not None:
                    height, width = arr.shape[:2]

            if result.masks is not None:
                label_data = _generate_labelme_payload(result, job.threshold, dest_path)
                if label_data:
                    label_path = _reserve_path(dest_path.with_suffix(".json"))
                    label_path.write_text(json.dumps(label_data, ensure_ascii=False, indent=2), encoding="utf-8")
            else:
                label_path = _reserve_path(dest_path.with_suffix(".xml"))
                _save_pascal_voc_xml(label_path, dest_path.name, width, height, boxes)

        return f"{image_path.name} -> {classification}/{sub_map[reason]} [{combo}]"


alg_test_manager = AlgTestManager()
