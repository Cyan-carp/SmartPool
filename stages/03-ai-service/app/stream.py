"""MJPEG 实时推流。

设计沿用已落地的人脸识别项目（Face_System 的 video_tracking.py），核心是三点：

1. **覆盖式帧槽**：只保留最新一帧，慢客户端自动丢帧，永不积压内存；
2. **按需推理**：viewer 数为 0 时暂停采集与推理，没人看就不烧算力；
3. **MJPEG 推送**：`multipart/x-mixed-replace`，浏览器 `<img>` 原生支持，
   不需要 WebSocket、不需要前端解码，比推 JSON + Canvas 重绘简单得多。

与原型项目的差异：这里复用 `app/frame` 的帧源抽象（文件/RTSP/摄像头/图片序列）
和 `app/detector` 的检测器，所以同一套推流代码既能接真实摄像头，也能放录像。

⚠️ 画面左上角会强制叠加来源标记（占位模型 / 真实权重），
   避免占位输出被误当成真实检测效果对外展示。
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field

from .detector.base import Detection, Detector, Frame
from .frame.base import FrameSource

logger = logging.getLogger(__name__)

try:
    import cv2
    import numpy as np
except ImportError:  # pragma: no cover - 依赖缺失由构造函数报错
    cv2 = None
    np = None


# 与前端设计令牌保持一致的 BGR 配色
COLOR_DROWNING = (114, 107, 255)  # #ff6b72
COLOR_SWIMMING = (245, 185, 67)  # #43b9f5
COLOR_UNKNOWN = (170, 152, 130)
COLOR_TEXT = (243, 233, 223)


class LatestFrameSlot:
    """覆盖式帧槽：永远只有最新一帧，慢客户端不会拖垮服务。"""

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._sequence = 0
        self._item: tuple[int, bytes] | None = None
        self._closed = False

    def put(self, jpeg: bytes) -> None:
        with self._condition:
            self._sequence += 1
            self._item = (self._sequence, jpeg)
            self._condition.notify_all()

    def get_after(self, sequence: int, timeout: float = 2.0) -> tuple[int, bytes] | None:
        with self._condition:
            self._condition.wait_for(
                lambda: self._closed or self._sequence > sequence, timeout=timeout
            )
            if self._closed or self._item is None or self._sequence <= sequence:
                return None
            return self._item

    def close(self) -> None:
        with self._condition:
            self._closed = True
            self._condition.notify_all()


class FpsMeter:
    def __init__(self, window_seconds: float = 5.0) -> None:
        self.window_seconds = window_seconds
        self._samples: deque[float] = deque()

    def tick(self) -> None:
        now = time.monotonic()
        self._samples.append(now)
        cutoff = now - self.window_seconds
        while self._samples and self._samples[0] < cutoff:
            self._samples.popleft()

    @property
    def value(self) -> float:
        if len(self._samples) < 2:
            return 0.0
        elapsed = self._samples[-1] - self._samples[0]
        return round((len(self._samples) - 1) / elapsed, 1) if elapsed > 0 else 0.0


@dataclass
class StreamStatus:
    running: bool = False
    error: str | None = None
    viewers: int = 0
    frames: int = 0
    fps: float = 0.0
    lastTargets: int = 0
    lastInferMs: float = 0.0
    modelLoaded: bool = False
    source: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "running": self.running,
            "error": self.error,
            "viewers": self.viewers,
            "frames": self.frames,
            "fps": self.fps,
            "lastTargets": self.lastTargets,
            "lastInferMs": self.lastInferMs,
            "modelLoaded": self.modelLoaded,
            "source": self.source,
        }


class VideoPublisher:
    """后台线程：取帧 -> 检测 -> 绘制 -> JPEG -> 覆盖帧槽。"""

    def __init__(
        self,
        source: FrameSource,
        detector: Detector,
        *,
        max_width: int = 960,
        quality: int = 75,
        conf: float | None = None,
        throttle_fps: float | None = None,
    ) -> None:
        if cv2 is None or np is None:
            raise RuntimeError("缺少 opencv/numpy，无法启用 MJPEG 推流")

        self._source = source
        self._detector = detector
        self._max_width = max(320, int(max_width))
        self._quality = max(30, min(95, int(quality)))
        self._conf = conf
        # 文件/图片序列会全速读，必须按源帧率节流，否则演示时画面"快进"；
        # RTSP 与摄像头本身是实时的，不需要（也不应该）限速。
        self._throttle_fps = throttle_fps if throttle_fps and throttle_fps > 0 else None
        self._next_deadline = 0.0

        self._slot = LatestFrameSlot()
        self._fps = FpsMeter()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._viewer_lock = threading.Lock()
        self._viewers = 0
        self._status = StreamStatus(
            modelLoaded=detector.model_loaded,
            source={
                "kind": source.meta.kind,
                "uri": source.meta.uri,
                "fps": source.meta.fps,
                "width": source.meta.width,
                "height": source.meta.height,
                "totalFrames": source.meta.total_frames,
            },
        )

    # ---------- 生命周期 ----------

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="video-publisher", daemon=True)
        self._thread.start()
        logger.info("推流线程已启动 uri=%s", self._source.meta.uri)

    def stop(self) -> None:
        self._stop.set()
        self._slot.close()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        self._source.close()
        self._status.running = False
        logger.info("推流已停止")

    # ---------- 观看者 ----------

    def add_viewer(self) -> None:
        with self._viewer_lock:
            self._viewers += 1
            self._status.viewers = self._viewers
        logger.info("viewer 加入，当前 %d", self._viewers)

    def remove_viewer(self) -> None:
        with self._viewer_lock:
            self._viewers = max(0, self._viewers - 1)
            self._status.viewers = self._viewers
        logger.info("viewer 离开，当前 %d", self._viewers)

    def wait_frame(self, last_sequence: int, timeout: float = 2.0) -> tuple[int, bytes] | None:
        return self._slot.get_after(last_sequence, timeout)

    def status(self) -> dict:
        self._status.fps = self._fps.value
        return self._status.to_dict()

    # ---------- 主循环 ----------

    def _loop(self) -> None:
        self._status.running = True
        idle_since: float | None = None

        while not self._stop.is_set():
            with self._viewer_lock:
                has_viewer = self._viewers > 0

            # 没人观看就暂停采集：不烧 CPU/GPU，也让摄像头可以休眠
            if not has_viewer:
                if idle_since is None:
                    idle_since = time.monotonic()
                time.sleep(0.1)
                continue
            idle_since = None

            captured = self._source.read()
            if captured is None:
                # 文件读完：loop 由帧源自己控制，这里只处理真正的结束
                self._status.running = False
                self._status.error = "帧源已结束"
                self._slot.close()
                logger.info("帧源结束，推流停止")
                return

            if self._throttle_fps:
                self._wait_next_slot()

            try:
                started = time.perf_counter()
                meta = {"frameIndex": captured.index, "timestampMs": captured.timestamp_ms}
                if self._conf is not None:
                    meta["conf"] = self._conf
                detections = self._detector.infer(Frame(image=captured.image, meta=meta))
                infer_ms = (time.perf_counter() - started) * 1000
                jpeg = self._render(captured.image, detections)
            except Exception as exc:  # noqa: BLE001 - 单帧失败不应终止整条流
                logger.exception("单帧处理失败: %s", exc)
                self._status.error = f"帧处理失败: {exc}"
                time.sleep(0.2)
                continue

            self._status.error = None
            self._status.frames += 1
            self._status.lastTargets = len(detections)
            self._status.lastInferMs = round(infer_ms, 2)
            self._fps.tick()
            self._slot.put(jpeg)

    def _wait_next_slot(self) -> None:
        """按目标帧率对齐输出节奏。

        落后超过一个节拍时不累积补偿，直接丢弃过期节拍，
        避免出现"欠账越多、播放越快"的追赶式快放。
        """
        interval = 1.0 / self._throttle_fps  # type: ignore[operator]
        now = time.monotonic()
        if self._next_deadline <= 0:
            self._next_deadline = now
        wait = self._next_deadline - now
        if wait > 0:
            time.sleep(wait)
        self._next_deadline = max(
            self._next_deadline + interval, time.monotonic() - interval
        )

    # ---------- 绘制与编码 ----------

    def _render(self, image, detections: list[Detection]) -> bytes:
        canvas = image
        height, width = canvas.shape[:2]

        # 超大分辨率先缩放，减小 JPEG 体积与推流带宽
        if width > self._max_width:
            scale = self._max_width / float(width)
            canvas = cv2.resize(canvas, (self._max_width, int(height * scale)), interpolation=cv2.INTER_AREA)
            height, width = canvas.shape[:2]

        for det in detections:
            self._draw_detection(canvas, det, width, height)

        self._draw_hud(canvas, detections)
        ok, buffer = cv2.imencode(
            ".jpg", canvas, [int(cv2.IMWRITE_JPEG_QUALITY), self._quality]
        )
        if not ok:
            raise RuntimeError("JPEG 编码失败")
        return buffer.tobytes()

    def _draw_detection(self, canvas, det: Detection, width: int, height: int) -> None:
        box = det.box
        x1 = int(box.get("x", 0.0) * width)
        y1 = int(box.get("y", 0.0) * height)
        x2 = int((box.get("x", 0.0) + box.get("w", 0.0)) * width)
        y2 = int((box.get("y", 0.0) + box.get("h", 0.0)) * height)
        x1, x2 = max(0, min(x1, width - 1)), max(0, min(x2, width - 1))
        y1, y2 = max(0, min(y1, height - 1)), max(0, min(y2, height - 1))

        posture = (det.posture or "").lower()
        if posture == "underwater_still":
            color = COLOR_DROWNING
        elif posture == "swimming":
            color = COLOR_SWIMMING
        else:
            color = COLOR_UNKNOWN

        thickness = max(1, int(round(width / 640)))
        cv2.rectangle(canvas, (x1, y1), (x2, y2), color, thickness)

        label = f"#{det.track_no}"
        if det.class_name:
            label += f" {det.class_name}"
        label += f" {det.confidence:.2f}"

        font_scale = max(0.4, width / 1600)
        (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)
        label_y = max(text_h + 4, y1 - 4)
        cv2.rectangle(
            canvas,
            (x1, label_y - text_h - 4),
            (x1 + text_w + 6, label_y + 2),
            color,
            -1,
        )
        cv2.putText(
            canvas,
            label,
            (x1 + 3, label_y - 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (16, 22, 29),
            1,
            cv2.LINE_AA,
        )

    def _draw_hud(self, canvas, detections: list[Detection]) -> None:
        """左上角状态条：必须让观看者一眼看出这是占位还是真实模型。

        ⚠️ 这里只能用 ASCII。OpenCV 的 Hershey 字体不含中文字形，
        直接画中文会输出一排问号；中文说明交给前端 HTML 叠加层去做。
        """
        placeholder = any(det.placeholder for det in detections) or not self._detector.model_loaded
        fps = self._status.fps if self._status.frames % 5 == 0 else self._fps.value
        source_kind = self._source.meta.kind

        if placeholder:
            badge = "[PLACEHOLDER] NOT REAL DETECTION"
            badge_color = COLOR_DROWNING
        else:
            badge = "[LIVE] MAMBA-YOLO"
            badge_color = (166, 209, 54)

        text = f"{badge} | {source_kind} | {fps:.1f} FPS | {len(detections)} targets"
        font_scale = 0.5
        (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)
        cv2.rectangle(canvas, (8, 8), (16 + text_w, 16 + text_h + 6), (18, 26, 33), -1)
        cv2.rectangle(canvas, (8, 8), (14, 16 + text_h + 6), badge_color, -1)
        cv2.putText(
            canvas,
            text,
            (20, 12 + text_h),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            COLOR_TEXT,
            1,
            cv2.LINE_AA,
        )
