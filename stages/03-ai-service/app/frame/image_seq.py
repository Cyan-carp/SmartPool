"""图片序列源。

用途：手头没有视频时，用数据集里的 test 图片按文件名顺序拼成一段"伪视频"，
先把"取帧 -> 检测 -> 结果落盘"整条链路跑通。

相比直接读视频，它的好处是完全可控：顺序固定、可复现、便于逐帧比对标注。
"""

from __future__ import annotations

import logging
from pathlib import Path

from .base import CapturedFrame, FrameSource, SourceMeta

logger = logging.getLogger(__name__)

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


class ImageSeqSource(FrameSource):
    def __init__(
        self,
        directory: str,
        fps: float = 10.0,
        loop: bool = False,
        max_frames: int = 0,
        recursive: bool = False,
    ) -> None:
        if cv2 is None:
            raise RuntimeError("缺少 opencv，请先 pip install -r requirements-ml.txt")

        root = Path(directory)
        if not root.is_dir():
            raise RuntimeError(f"图片目录不存在: {directory}")

        files = [
            item
            for item in (root.rglob("*") if recursive else root.glob("*"))
            if item.is_file() and item.suffix.lower() in IMAGE_SUFFIXES
        ]
        if not files:
            raise RuntimeError(f"目录内没有可用图片: {directory}")

        self._files = sorted(files, key=lambda item: item.name)
        self._fps = fps if fps > 0 else 10.0
        self._loop = loop
        self._max_frames = max(0, int(max_frames))
        self._cursor = 0
        self._out_index = 0
        self._closed = False

        self._meta = SourceMeta(
            kind="image_seq",
            uri=str(root),
            fps=self._fps,
            total_frames=len(self._files),
            loop=loop,
            extra={"recursive": recursive, "first": self._files[0].name},
        )
        logger.info("图片序列已就绪 dir=%s count=%d fps=%.1f", root, len(self._files), self._fps)

    @property
    def meta(self) -> SourceMeta:
        return self._meta

    def read(self) -> CapturedFrame | None:
        if self._closed:
            return None
        if self._max_frames and self._out_index >= self._max_frames:
            return None
        if self._cursor >= len(self._files):
            if not self._loop:
                return None
            self._cursor = 0

        path = self._files[self._cursor]
        image = cv2.imread(str(path))
        if image is None:
            logger.warning("图片无法解码，已跳过: %s", path)
            self._cursor += 1
            return self.read()

        source_index = self._cursor
        self._cursor += 1

        frame = CapturedFrame(
            index=self._out_index,
            source_index=source_index,
            timestamp_ms=round(source_index / self._fps * 1000, 1),
            image=image,
        )
        self._out_index += 1
        frame.image  # noqa: B018 - 保持与 video.py 一致的返回形态
        return frame

    def close(self) -> None:
        self._closed = True
