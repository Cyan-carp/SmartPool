"""帧源抽象。

取帧是"真实模型链路"的第一环，也是最容易和现场环境绑死的一环：
调试时读本地视频、演示时读录像、部署时读 RTSP 或摄像头。
把这三者收敛到同一个 `FrameSource` 接口，上层（检测、跟踪、风险、推送）
就完全不需要知道帧从哪来。

约定：
  · 图像统一为 BGR 三通道 ndarray，与 OpenCV / Ultralytics 的默认一致
  · `read()` 返回 None 表示本次没有新帧（结束或暂时无数据），不抛异常
  · 调用方负责 `close()`，或用 with 语句自动释放
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

try:
    import numpy as np

    NDArray = np.ndarray
except ImportError:  # pragma: no cover - 无 numpy 时不应走到取帧
    NDArray = Any  # type: ignore[misc,assignment]


@dataclass
class SourceMeta:
    """帧源的基本信息，用于日志、健康检查与结果文件归档。"""

    kind: str  # file | rtsp | camera | image_seq
    uri: str
    fps: float
    width: int = 0
    height: int = 0
    # 0 表示未知（直播流、摄像头）
    total_frames: int = 0
    loop: bool = False
    extra: dict = field(default_factory=dict)


@dataclass
class CapturedFrame:
    """一帧图像及其时间信息。

    index 是"输出序号"（抽帧之后），source_index 是源里的原始帧号。
    两者分开是因为 stride > 1 时会跳帧，排查问题时需要能定位回原视频。
    """

    index: int
    source_index: int
    timestamp_ms: float
    image: "NDArray"


class FrameSource(ABC):
    """所有帧源的统一入口。"""

    @property
    @abstractmethod
    def meta(self) -> SourceMeta:
        """帧源元信息。"""

    @abstractmethod
    def read(self) -> CapturedFrame | None:
        """读下一帧。返回 None 表示结束或当前无帧。"""

    @abstractmethod
    def close(self) -> None:
        """释放底层资源。可重复调用。"""

    def __enter__(self) -> "FrameSource":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
