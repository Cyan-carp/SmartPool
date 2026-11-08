"""取帧 -> 检测 的最小流水线。

刻意不在这里做跟踪和风险打分：
  · 跟踪属于检测器内部（MambaYoloDetector 自带 IoU 关联）
  · 风险打分有跨帧状态，应由调用方持有（主服务一份、离线脚本一份）

这样同一段流水线既能服务实时接口，也能被离线预生成脚本复用，
保证"演示看到的"和"报告里写的"出自同一套代码。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Iterator

from .detector.base import Detection, Detector, Frame
from .frame.base import FrameSource


@dataclass
class InferenceRecord:
    """单帧的推理结果，可直接序列化成 JSON 供前端回放。"""

    frame_index: int
    source_index: int
    timestamp_ms: float
    infer_ms: float
    detections: list[Detection] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "index": self.frame_index,
            "sourceIndex": self.source_index,
            "ts": self.timestamp_ms,
            "inferMs": self.infer_ms,
            "count": len(self.detections),
            "targets": [
                {
                    "trackNo": det.track_no,
                    "box": det.box,
                    "confidence": det.confidence,
                    "posture": det.posture,
                    "className": det.class_name,
                    "placeholder": det.placeholder,
                }
                for det in self.detections
            ],
        }


ProgressHook = Callable[[int, InferenceRecord], None]


def iter_detections(
    source: FrameSource,
    detector: Detector,
    *,
    conf: float | None = None,
    imgsz: int | None = None,
    max_frames: int = 0,
    on_progress: ProgressHook | None = None,
    progress_every: int = 0,
) -> Iterator[InferenceRecord]:
    """逐帧取图并检测。

    帧源读尽、或达到 max_frames 时结束。检测器对空输入会返回空列表，
    不抛异常，保证一段坏帧不会中断整段视频的处理。
    """
    produced = 0
    while True:
        if max_frames and produced >= max_frames:
            return

        captured = source.read()
        if captured is None:
            return

        meta: dict = {
            "frameIndex": captured.index,
            "sourceIndex": captured.source_index,
            "timestampMs": captured.timestamp_ms,
        }
        if conf is not None:
            meta["conf"] = conf
        if imgsz is not None:
            meta["imgsz"] = imgsz

        started = time.perf_counter()
        detections: list[Detection] = detector.infer(Frame(image=captured.image, meta=meta))
        infer_ms = round((time.perf_counter() - started) * 1000, 2)

        record = InferenceRecord(
            frame_index=captured.index,
            source_index=captured.source_index,
            timestamp_ms=captured.timestamp_ms,
            infer_ms=infer_ms,
            detections=detections,
        )
        produced += 1

        if on_progress and progress_every and produced % progress_every == 0:
            on_progress(produced, record)

        yield record
