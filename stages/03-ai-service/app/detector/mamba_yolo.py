"""Mamba-YOLO 真实检测实现（骨架）。

接入三步：
  1) 安装 ML 依赖      pip install -r requirements-ml.txt
  2) 指定权重路径      AI_MODEL_PATH=/models/mambayolo9_best.pt
  3) 切换提供者        AI_DETECTOR_PROVIDER=mamba-yolo

口径说明（涉及结题材料真实性，勿删改）：
  · 本项目模型是「溺水 / 游泳」两类目标检测，输出只有类别与检测框，
    不含人体关键点。
  · 所以 posture 由类别粗映射得到，是行为标签而非姿态识别结果；
    对外表述一律用"溺水分级判定"，不要写"姿态关键点检测"。
  · 后续若接入关键点模型，只需替换 map_posture() 一处，
    下游 RiskScorer 与前端协议都不用动。

坐标：模型输出像素坐标，这里统一转成 0~1 归一化的 {x,y,w,h}，
      与前端叠加层、RiskScorer 的静止判定口径保持一致。
"""

from __future__ import annotations

import logging

from .base import Detection, Detector, Frame

logger = logging.getLogger(__name__)

# 类别名 -> 行为标签。二分类模型只能给出这两个值。
# drowning 映射为 underwater_still 会直接参与 RiskScorer 的"头部未出水"累计，
# 即持续检测到溺水时风险分会在 25 秒内升至满值 —— 这是预期行为。
CLASS_POSTURE = {
    "drowning": "underwater_still",
    "swimming": "swimming",
}


def map_posture(class_name: str) -> str:
    return CLASS_POSTURE.get(class_name.strip().lower(), "unknown")


def _iou(a: dict, b: dict) -> float:
    ax1, ay1 = a["x"], a["y"]
    ax2, ay2 = ax1 + a["w"], ay1 + a["h"]
    bx1, by1 = b["x"], b["y"]
    bx2, by2 = bx1 + b["w"], by1 + b["h"]
    iw = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    ih = max(0.0, min(ay2, by2) - max(ay1, by1))
    inter = iw * ih
    if inter <= 0:
        return 0.0
    union = a["w"] * a["h"] + b["w"] * b["h"] - inter
    return inter / union if union > 0 else 0.0


class _IouTracker:
    """极简 IoU 关联，只负责给检测框分配稳定的 track_no。

    下游 RiskScorer 按 track_no 累计"静止时长 / 头部未出水时长"，
    没有稳定 ID 时风险判定会失效，所以这一步是必需的。

    TODO 换成 ByteTrack（ultralytics 内置 bytetrack.yaml / botsort.yaml）
         后可直接删除本类，改为 result.boxes.id。
    """

    def __init__(self, iou_threshold: float = 0.3, max_missed: int = 30) -> None:
        self.iou_threshold = iou_threshold
        self.max_missed = max_missed
        self._tracks: dict[int, dict] = {}
        self._next_id = 1
        self._frame_no = 0

    def update(self, boxes: list[dict]) -> list[int]:
        self._frame_no += 1
        assigned: list[int] = []
        used: set[int] = set()

        for box in boxes:
            best_id: int | None = None
            best_iou = self.iou_threshold
            for track_id, track in self._tracks.items():
                if track_id in used:
                    continue
                score = _iou(box, track["box"])
                if score > best_iou:
                    best_id, best_iou = track_id, score
            if best_id is None:
                best_id = self._next_id
                self._next_id += 1
            used.add(best_id)
            self._tracks[best_id] = {"box": box, "last": self._frame_no}
            assigned.append(best_id)

        self._tracks = {
            track_id: track
            for track_id, track in self._tracks.items()
            if self._frame_no - track["last"] <= self.max_missed
        }
        return assigned

    def reset(self) -> None:
        self._tracks.clear()
        self._next_id = 1
        self._frame_no = 0


class MambaYoloDetector(Detector):
    name = "mamba-yolo"

    def __init__(self) -> None:
        self._model = None
        self._device = "cpu"
        self._loaded = False
        self._classes: dict[int, str] = {}
        self._tracker = _IouTracker()
        self._imgsz = 640
        self._conf = 0.25

    def load(self, model_path: str | None, device: str) -> None:
        if not model_path:
            raise RuntimeError(
                "AI_MODEL_PATH 未配置，无法加载 Mamba-YOLO 权重；"
                "请指向 mambayolo9/weights/best.pt"
            )
        try:
            from ultralytics import YOLO
        except ImportError as exc:  # pragma: no cover - 依赖缺失时给出明确指引
            raise RuntimeError(
                "缺少 ultralytics 依赖，请先 pip install -r requirements-ml.txt"
            ) from exc

        self._model = YOLO(model_path)
        self._device = device or "cpu"
        names = getattr(self._model, "names", None) or {}
        self._classes = {int(key): str(value) for key, value in dict(names).items()}
        self._loaded = True
        logger.info(
            "Mamba-YOLO 已加载 path=%s device=%s classes=%s",
            model_path,
            self._device,
            self._classes,
        )

    @property
    def model_loaded(self) -> bool:
        return self._loaded

    def infer(self, frame: Frame) -> list[Detection]:
        if not self._loaded or self._model is None:
            return []
        if frame.image is None:
            # 演示链路喂的是世界状态而非图像，真实实现无输入可用
            logger.debug("MambaYoloDetector 收到非图像帧，已跳过")
            return []

        meta = frame.meta or {}
        conf = float(meta.get("conf", self._conf))
        imgsz = int(meta.get("imgsz", self._imgsz))

        results = self._model.predict(
            source=frame.image,
            conf=conf,
            imgsz=imgsz,
            device=self._device,
            verbose=False,
        )
        if not results:
            return []

        result = results[0]
        height, width = frame.image.shape[:2]
        if height <= 0 or width <= 0:
            return []

        boxes: list[dict] = []
        payloads: list[tuple[float, str]] = []
        for raw in result.boxes:
            x1, y1, x2, y2 = (float(v) for v in raw.xyxy[0].tolist())
            cls_id = int(raw.cls[0]) if raw.cls is not None else -1
            class_name = self._classes.get(cls_id, str(cls_id))
            boxes.append(
                {
                    "x": round(max(0.0, min(1.0, x1 / width)), 4),
                    "y": round(max(0.0, min(1.0, y1 / height)), 4),
                    "w": round(max(0.0, min(1.0, (x2 - x1) / width)), 4),
                    "h": round(max(0.0, min(1.0, (y2 - y1) / height)), 4),
                }
            )
            payloads.append((float(raw.conf[0]), class_name))

        track_ids = self._tracker.update(boxes)

        detections: list[Detection] = []
        for track_no, box, (confidence, class_name) in zip(track_ids, boxes, payloads):
            detections.append(
                Detection(
                    track_no=track_no,
                    box=box,
                    confidence=round(confidence, 4),
                    posture=map_posture(class_name),
                    class_name=class_name,
                    placeholder=False,
                )
            )
        return detections

    def reset(self) -> None:
        """清空跟踪状态（场景切换或 /reset 时调用）。"""
        self._tracker.reset()
