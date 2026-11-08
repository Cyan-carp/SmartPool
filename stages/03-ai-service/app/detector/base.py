"""检测器抽象。

输入统一为 `Frame`，它有两种互斥来源：
  · snapshot —— 演示版的"世界状态"，目标位置已由模拟器给出（MockDetector 使用）
  · image    —— 真实图像帧（MambaYoloDetector 使用）

这样同一套上游（跟踪、风险打分、后端、前端协议）既能跑合成数据，
也能在接入真实模型后原样复用，只需切换 AI_DETECTOR_PROVIDER。

切换真实 Mamba-YOLO：实现类见 mamba_yolo.py，上层无需改动。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

# 不在 mock 模式下强依赖 numpy：缺失时类型退化为 Any，不影响占位实现运行
try:
    import numpy as np

    NDArray = np.ndarray
except ImportError:  # pragma: no cover - 占位运行时走这里
    NDArray = Any  # type: ignore[misc,assignment]


@dataclass
class Frame:
    """一帧待检测输入。snapshot 与 image 互斥，实现类各取所需。"""

    snapshot: dict | None = None
    image: "NDArray | None" = None
    meta: dict = field(default_factory=dict)

    @property
    def is_image(self) -> bool:
        return self.image is not None


@dataclass
class Detection:
    track_no: int
    # 归一化坐标（左上角 + 宽高），取值范围 0~1，与前端叠加层一致
    box: dict
    confidence: float
    # 粗粒度行为标签，取值见 POSTURES；不是人体关键点姿态
    posture: str
    group: str = "ADULT"
    wristband: str | None = None
    wristband_data: dict | None = None
    # True 表示该结果由占位实现产生，前端必须如实展示"占位模式"
    placeholder: bool = True
    # 检测器原始类别名（Drowning / Swimming），便于排查与统计
    class_name: str = ""
    extra: dict = field(default_factory=dict)


# 下游 RiskScorer 只对 underwater_still / floating 做静止累计，其余按正常行为处理
POSTURES = ("swimming", "treading", "floating", "underwater_still", "standing", "unknown")


class Detector(ABC):
    """所有检测实现的统一入口。"""

    name: str = "base"

    @abstractmethod
    def load(self, model_path: str | None, device: str) -> None:
        """加载权重。占位实现为空操作。"""

    @abstractmethod
    def infer(self, frame: Frame) -> list[Detection]:
        """对一帧输入做检测。

        占位实现读取 frame.snapshot；真实实现读取 frame.image。
        输入类型不匹配时应返回空列表并在日志中说明，不要抛异常打断链路。
        """

    @property
    @abstractmethod
    def model_loaded(self) -> bool:
        """真实权重是否已加载。占位实现恒为 False。"""

    @property
    def info(self) -> dict:
        """供 /health 与前端"模型与算力"页展示的静态元信息。"""
        return {
            "provider": self.name,
            "modelLoaded": self.model_loaded,
            "placeholder": not self.model_loaded,
        }
