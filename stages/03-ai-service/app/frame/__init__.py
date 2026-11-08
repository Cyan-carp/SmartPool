"""帧源工厂。

上层只需要 `create_source(uri)`，不关心背后是视频文件、RTSP、摄像头还是图片序列。
换数据源只改配置，不改代码。
"""

from __future__ import annotations

from pathlib import Path

from .base import CapturedFrame, FrameSource, SourceMeta
from .image_seq import ImageSeqSource
from .video import VideoSource, describe_video

__all__ = [
    "CapturedFrame",
    "FrameSource",
    "SourceMeta",
    "ImageSeqSource",
    "VideoSource",
    "create_source",
    "detect_kind",
    "describe_video",
]


def detect_kind(uri: str) -> str:
    """按 uri 形态推断帧源类型。"""
    text = uri.strip()
    if not text:
        raise ValueError("帧源地址为空")
    if Path(text).is_dir():
        return "image_seq"
    lowered = text.lower()
    if lowered.startswith(("rtsp://", "rtmp://", "http://", "https://")):
        return "rtsp"
    if text.isdigit():
        return "camera"
    return "file"


def create_source(
    uri: str,
    *,
    kind: str | None = None,
    stride: int = 1,
    loop: bool = False,
    fps: float | None = None,
    max_frames: int = 0,
) -> FrameSource:
    """创建帧源。

    Args:
        uri: 文件路径 / rtsp:// / 摄像头索引（"0"）/ 图片目录
        kind: 强制指定类型，缺省按 uri 推断
        stride: 抽帧间隔，每 stride 帧取 1 帧（仅对视频流有效）
        loop: 读到末尾是否循环（图片序列与文件都支持，直播流忽略）
        fps: 覆盖帧率，摄像头/流常返回 0，可在此修正
        max_frames: 最多输出多少帧，0 表示不限制
    """
    resolved = kind or detect_kind(uri)
    if resolved == "image_seq":
        return ImageSeqSource(uri, fps=fps or 10.0, loop=loop, max_frames=max_frames)
    return VideoSource(
        uri,
        stride=stride,
        loop=loop,
        fps_override=fps,
        max_frames=max_frames,
    )
