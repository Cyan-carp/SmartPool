"""视频文件 / RTSP 流 / 本地摄像头。

三者底层都是 OpenCV 的 VideoCapture，差别只在 source 字符串：
    文件    ./demo.mp4
    RTSP    rtsp://user:pass@192.168.1.10:554/stream1
    摄像头  0（整数索引，对应 /dev/video0 或 Windows 的第一个摄像头）

抽帧用 stride：每 stride 帧取 1 帧。泳池场景 25fps 里相邻帧几乎没有差异，
按 5 抽 1 就是 5fps，足够做风险判定，还能把推理负载降到 1/5。

RTSP 断流是常态（网络抖动、摄像头重启），这里做了有限次重连；
文件读完则按 loop 决定回到开头还是结束。
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from .base import CapturedFrame, FrameSource, SourceMeta

logger = logging.getLogger(__name__)

try:
    import cv2
except ImportError:  # pragma: no cover - 依赖缺失由构造函数报错
    cv2 = None


def _as_capture_id(uri: str) -> int | str:
    """纯数字串视为摄像头索引。"""
    text = uri.strip()
    if text.isdigit():
        return int(text)
    return text


class VideoSource(FrameSource):
    def __init__(
        self,
        uri: str,
        stride: int = 1,
        loop: bool = False,
        fps_override: float | None = None,
        max_frames: int = 0,
        reconnect_attempts: int = 2,
    ) -> None:
        if cv2 is None:
            raise RuntimeError(
                "缺少 opencv，请先 pip install -r requirements-ml.txt"
            )

        self._uri = uri
        self._stride = max(1, int(stride))
        self._loop = loop
        self._fps_override = fps_override
        self._max_frames = max(0, int(max_frames))
        self._reconnect_attempts = max(0, int(reconnect_attempts))

        self._cap = None
        self._out_index = 0
        self._source_index = 0
        self._eof = False
        self._closed = False
        self._meta: SourceMeta | None = None

        self._open()

    def _open(self) -> None:
        capture_id = _as_capture_id(self._uri)
        cap = cv2.VideoCapture(capture_id)
        if not cap.isOpened():
            raise RuntimeError(f"无法打开视频源: {self._uri}")

        # 直播流缓冲区压到最小，避免读到几秒前的画面
        try:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:  # pragma: no cover - 部分后端不支持
            pass

        fps = self._fps_override or float(cap.get(cv2.CAP_PROP_FPS) or 0)
        if fps <= 0 or fps > 240:
            fps = 25.0  # 摄像头/流常返回 0 或离谱值，给个合理默认

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if total < 0:
            total = 0

        is_stream = self._uri.strip().lower().startswith(("rtsp://", "rtmp://", "http://", "https://"))
        kind = "rtsp" if is_stream else ("camera" if self._uri.strip().isdigit() else "file")

        self._cap = cap
        self._meta = SourceMeta(
            kind=kind,
            uri=self._uri,
            fps=fps,
            width=width,
            height=height,
            total_frames=total,
            loop=self._loop,
            extra={"isStream": is_stream},
        )
        self._eof = False
        self._source_index = 0
        logger.info(
            "视频源已打开 kind=%s uri=%s fps=%.1f size=%dx%d total=%d stride=%d",
            kind,
            self._uri,
            fps,
            width,
            height,
            total,
            self._stride,
        )

    @property
    def meta(self) -> SourceMeta:
        assert self._meta is not None
        return self._meta

    def read(self) -> CapturedFrame | None:
        if self._closed or self._cap is None:
            return None
        if self._max_frames and self._out_index >= self._max_frames:
            return None

        # 跳过 stride-1 帧
        for _ in range(self._stride - 1):
            if not self._cap.grab():
                break

        ok, image = self._cap.read()
        if not ok or image is None:
            return self._handle_eof()

        source_index = self._source_index
        self._source_index += self._stride

        frame = CapturedFrame(
            index=self._out_index,
            source_index=source_index,
            timestamp_ms=round(source_index / self.meta.fps * 1000, 1),
            image=image,
        )
        self._out_index += 1
        return frame

    def _handle_eof(self) -> CapturedFrame | None:
        # 文件读到末尾：按 loop 决定重播还是结束
        if self.meta.total_frames > 0:
            if self._loop:
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self._source_index = 0
                logger.info("视频回放至开头 uri=%s", self._uri)
                return self.read()
            self._eof = True
            return None

        # 流断开：有限次重连，避免一个摄像头抖动把整条链路卡死
        if self._eof:
            return None
        for attempt in range(1, self._reconnect_attempts + 1):
            logger.warning("视频源断开，第 %d 次重连 uri=%s", attempt, self._uri)
            time.sleep(min(2.0, 0.5 * attempt))
            try:
                self._cap.release()
                self._open()
                ok, image = self._cap.read()
                if ok and image is not None:
                    logger.info("视频源重连成功 uri=%s", self._uri)
                    frame = CapturedFrame(
                        index=self._out_index,
                        source_index=self._source_index,
                        timestamp_ms=round(self._source_index / self.meta.fps * 1000, 1),
                        image=image,
                    )
                    self._out_index += 1
                    self._source_index += self._stride
                    return frame
            except Exception as exc:  # pragma: no cover - 依赖运行时环境
                logger.warning("重连失败: %s", exc)
        self._eof = True
        return None

    @property
    def exhausted(self) -> bool:
        return self._eof

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        logger.info("视频源已关闭 uri=%s", self._uri)


def describe_video(uri: str) -> dict:
    """不取帧、只读元信息，供 /health 与调试接口使用。"""
    if cv2 is None:
        return {"ok": False, "error": "opencv 未安装"}
    path = Path(uri)
    if path.exists():
        return {"ok": True, "kind": "file", "sizeBytes": path.stat().st_size}
    return {"ok": True, "kind": "stream", "uri": uri}
