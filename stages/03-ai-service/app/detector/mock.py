"""占位检测器：按世界状态生成带噪声的检测框。

不加载任何权重，输出带 placeholder=True 标记，前端必须展示「占位模式」。
"""

from __future__ import annotations

import random

from .base import Detection, Detector, Frame


class MockDetector(Detector):
    name = "mock"

    def __init__(self, seed: int = 2026) -> None:
        self._rng = random.Random(seed)
        self._loaded = False

    def load(self, model_path: str | None, device: str) -> None:
        # 占位实现不加载权重
        self._loaded = False

    @property
    def model_loaded(self) -> bool:
        return self._loaded

    def infer(self, frame: Frame) -> list[Detection]:
        # 占位实现只认世界状态；收到真实图像时按空结果处理，交由调用方提示
        snapshot = frame.snapshot or {}
        detections: list[Detection] = []
        for target in snapshot.get("targets", []):
            box = target.get("box", {})
            jitter = 0.002
            noisy_box = {
                "x": round(max(0.0, min(1.0, box.get("x", 0) + self._rng.uniform(-jitter, jitter))), 4),
                "y": round(max(0.0, min(1.0, box.get("y", 0) + self._rng.uniform(-jitter, jitter))), 4),
                "w": round(box.get("w", 0.05), 4),
                "h": round(box.get("h", 0.07), 4),
            }
            confidence = round(self._rng.uniform(0.72, 0.97), 3)
            detections.append(Detection(
                track_no=target.get("trackNo", 0),
                box=noisy_box,
                confidence=confidence,
                posture=target.get("posture", "unknown"),
                group=target.get("group", "ADULT"),
                wristband=target.get("wristband"),
                wristband_data=target.get("wristbandData"),
                placeholder=True,
            ))
        return detections
