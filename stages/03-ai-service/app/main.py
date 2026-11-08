"""推理服务（8000）：检测 -> 跟踪号 -> 风险打分。

演示版使用 MockDetector，`modelLoaded` 恒为 False，输出带 placeholder 标记。
替换真实模型的唯一入口见 README。
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .detector.base import Detector, Frame
from .detector.mock import MockDetector
from .risk.scorer import RiskScorer

logger = logging.getLogger(__name__)

VERSION = "0.1.0"
SIMULATOR_URL = os.getenv("SIMULATOR_URL", "http://localhost:8010")
PROVIDER = os.getenv("AI_DETECTOR_PROVIDER", "mock")
MODEL_PATH = os.getenv("AI_MODEL_PATH", "")
DEVICE = os.getenv("AI_DEVICE", "cpu")

PARAMS = {
    "PEAK": {"confidence": 0.70, "windowT": 30, "stride": "1x1", "computeRatio": 1.0},
    "OFFPEAK": {"confidence": 0.85, "windowT": 60, "stride": "2x2", "computeRatio": 0.68},
}

scorer = RiskScorer()
mode = {"value": "PEAK"}
last_infer_at = {"value": 0.0}


def build_detector() -> Detector:
    """按环境变量选择检测实现。

    真实实现不静默降级：配置了 mamba-yolo 却加载失败时直接启动失败，
    避免"以为接了真模型、实际还在跑占位"这种最危险的误判。
    """
    if PROVIDER in ("mamba-yolo", "mamba_yolo"):
        from .detector.mamba_yolo import MambaYoloDetector

        return MambaYoloDetector()
    if PROVIDER != "mock":
        logger.warning("未知的 AI_DETECTOR_PROVIDER=%s，已回退到 mock", PROVIDER)
    return MockDetector()


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


detector = build_detector()
detector.load(MODEL_PATH or None, DEVICE)

# ---------- 实时推流（可选） ----------
# AI_VIDEO_SOURCE 为空时整条推流链路不启用，服务行为与之前完全一致。
VIDEO_SOURCE = os.getenv("AI_VIDEO_SOURCE", "").strip()
VIDEO_STRIDE = _env_int("AI_VIDEO_STRIDE", 1)
VIDEO_FPS = os.getenv("AI_VIDEO_FPS", "").strip()
STREAM_MAX_WIDTH = _env_int("AI_STREAM_MAX_WIDTH", 960)
STREAM_QUALITY = _env_int("AI_STREAM_QUALITY", 75)
REPLAY_DIR = Path(os.getenv("AI_REPLAY_DIR", "artifacts"))

publisher = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global publisher
    if VIDEO_SOURCE:
        try:
            from .frame import create_source
            from .stream import VideoPublisher

            source = create_source(
                VIDEO_SOURCE,
                stride=VIDEO_STRIDE,
                loop=True,
                fps=float(VIDEO_FPS) if VIDEO_FPS else None,
            )
            # 文件与图片序列是离线源，不节流会全速播放；直播源本身就实时
            throttle = None
            if source.meta.kind in ("file", "image_seq"):
                throttle = max(1.0, source.meta.fps) / max(1, VIDEO_STRIDE)
            publisher = VideoPublisher(
                source,
                detector,
                max_width=STREAM_MAX_WIDTH,
                quality=STREAM_QUALITY,
                throttle_fps=throttle,
            )
            publisher.start()
            logger.info("实时推流已启用 source=%s", VIDEO_SOURCE)
        except Exception as exc:  # noqa: BLE001 - 推流失败不应让接口服务起不来
            logger.exception("实时推流初始化失败，服务继续以接口模式运行: %s", exc)
            publisher = None
    else:
        logger.info("未配置 AI_VIDEO_SOURCE，推流功能关闭")

    yield

    if publisher is not None:
        publisher.stop()


app = FastAPI(title="SmartPool AI Service", version=VERSION, lifespan=lifespan)


class ModeRequest(BaseModel):
    mode: str = Field(default="PEAK", pattern="^(PEAK|OFFPEAK)$")
    auto: bool = True


@app.get("/health")
def health() -> dict:
    simulator_ok = False
    try:
        resp = httpx.get(f"{SIMULATOR_URL}/health", timeout=2.0)
        simulator_ok = resp.status_code == 200
    except httpx.HTTPError:
        simulator_ok = False
    return {
        "ok": True,
        "service": "smartpool-ai",
        "version": VERSION,
        "provider": PROVIDER,
        "modelLoaded": detector.model_loaded,
        "placeholder": not detector.model_loaded,
        "device": DEVICE,
        "mode": mode["value"],
        "simulatorReachable": simulator_ok,
    }


@app.post("/infer")
def infer(poolId: int = 1) -> dict:
    started = time.perf_counter()
    try:
        resp = httpx.get(f"{SIMULATOR_URL}/sim/snapshot", params={"poolId": poolId}, timeout=2.0)
        resp.raise_for_status()
        snapshot = resp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail=f"模拟数据源不可用: {exc}")

    now = time.time()
    dt = min(2.0, max(0.05, now - last_infer_at["value"])) if last_infer_at["value"] else 0.5
    last_infer_at["value"] = now

    params = PARAMS[mode["value"]]
    threshold = params["confidence"]

    # 演示链路喂的是世界状态快照；真实图像应走 /infer/image 或由视频接入模块直接调 detector
    detections = detector.infer(
        Frame(snapshot=snapshot, meta={"poolId": poolId, "conf": threshold})
    )
    placeholder = not detector.model_loaded

    targets = []
    for det in detections:
        if det.confidence < threshold:
            continue
        risk = scorer.score(det, dt)
        targets.append({
            "trackNo": det.track_no,
            "box": det.box,
            "confidence": det.confidence,
            "posture": det.posture,
            "class_name": det.class_name,
            "group": det.group,
            "wristband": det.wristband,
            "wristbandData": det.wristband_data,
            "riskScore": risk.score,
            "level": risk.level,
            "reason": risk.reason,
            "riskDetail": risk.detail,
            "placeholder": det.placeholder,
            # 该链路的数据恒为模拟器合成，与模型是否真实无关
            "synthetic": True,
        })

    infer_ms = round((time.perf_counter() - started) * 1000, 1)
    return {
        "poolId": poolId,
        "ts": datetime.now().astimezone().isoformat(timespec="milliseconds"),
        "seq": snapshot.get("seq", 0),
        "provider": PROVIDER,
        "modelLoaded": detector.model_loaded,
        "placeholder": placeholder,
        "inferMs": infer_ms,
        "mode": mode["value"],
        "params": params,
        "scenario": snapshot.get("scenario", "normal"),
        "targets": targets,
        "counts": snapshot.get("counts", {}),
        "water": snapshot.get("water", {}),
        "synthetic": True,
    }


@app.post("/infer/image")
async def infer_image(file: UploadFile = File(...), poolId: int = 1) -> dict:
    """用上传图片联调真实模型，不参与演示链路。

    真实部署时由视频接入模块直接构造 Frame(image=...) 喂帧；
    这个端点只用于回答"模型接对没有"，所以不做风险累计（会污染主链路状态）。
    """
    if not detector.model_loaded:
        raise HTTPException(status_code=409, detail="当前检测器为占位实现，未加载真实权重")

    try:
        import cv2
        import numpy as np
    except ImportError as exc:  # pragma: no cover
        raise HTTPException(status_code=503, detail=f"缺少图像依赖: {exc}") from exc

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="上传内容为空")
    image = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="无法解析图片，请上传 jpg/png")

    started = time.perf_counter()
    detections = detector.infer(
        Frame(image=image, meta={"poolId": poolId, "conf": PARAMS[mode["value"]]["confidence"]})
    )
    infer_ms = round((time.perf_counter() - started) * 1000, 1)

    return {
        "poolId": poolId,
        "provider": PROVIDER,
        "modelLoaded": detector.model_loaded,
        "placeholder": False,
        "synthetic": False,
        "imageSize": {"width": int(image.shape[1]), "height": int(image.shape[0])},
        "inferMs": infer_ms,
        "targets": [
            {
                "trackNo": det.track_no,
                "box": det.box,
                "confidence": det.confidence,
                "posture": det.posture,
                "className": det.class_name,
                "placeholder": det.placeholder,
            }
            for det in detections
        ],
    }


@app.get("/stream.mjpg")
def stream_mjpeg() -> StreamingResponse:
    """MJPEG 实时画面。

    浏览器 <img src> 直接可用，前端不需要解码，也不用 WebSocket。
    每个连接算一个 viewer；viewer 数归零时后台线程停止采集与推理。
    """
    if publisher is None:
        raise HTTPException(
            status_code=503,
            detail="推流未启用：需要在 AI_VIDEO_SOURCE 指定视频文件、RTSP 或摄像头索引",
        )

    publisher.add_viewer()

    def generate() -> Iterator[bytes]:
        sequence = 0
        try:
            while True:
                item = publisher.wait_frame(sequence, timeout=2.0)
                if item is None:
                    if not publisher.status()["running"]:
                        break
                    continue
                sequence, jpeg = item
                header = (
                    b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                    + str(len(jpeg)).encode("ascii")
                    + b"\r\n\r\n"
                )
                yield header + jpeg + b"\r\n"
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            # 客户端关页面属于正常现象，不当作错误
            pass
        finally:
            publisher.remove_viewer()

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
    )


@app.get("/stream/status")
def stream_status() -> dict:
    if publisher is None:
        return {
            "enabled": False,
            "reason": "AI_VIDEO_SOURCE 未配置",
            "modelLoaded": detector.model_loaded,
        }
    return {"enabled": True, **publisher.status()}


@app.get("/replay/list")
def replay_list() -> dict:
    """列出可回放的离线检测结果（由 tools/pregenerate.py 产出）。"""
    if not REPLAY_DIR.is_dir():
        return {"items": [], "dir": str(REPLAY_DIR)}
    items = []
    for path in sorted(
        REPLAY_DIR.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True
    )[:50]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        summary = data.get("summary") or {}
        source = data.get("source") or {}
        items.append(
            {
                "name": path.name,
                "sizeKb": round(path.stat().st_size / 1024, 1),
                "generatedAt": data.get("generatedAt"),
                "provider": data.get("provider"),
                "modelLoaded": data.get("modelLoaded"),
                "frames": summary.get("frames", 0),
                "targets": summary.get("targets", 0),
                "avgInferMs": summary.get("avgInferMs"),
                "source": source.get("uri"),
            }
        )
    return {"items": items, "dir": str(REPLAY_DIR.resolve())}


@app.get("/replay/{name}")
def replay_detail(name: str) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_\-.]+\.json", name):
        raise HTTPException(status_code=400, detail="非法的回放文件名")

    base = REPLAY_DIR.resolve()
    path = (base / name).resolve()
    if base not in path.parents:
        raise HTTPException(status_code=400, detail="路径越界")

    if not path.is_file():
        raise HTTPException(status_code=404, detail="回放文件不存在")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"回放文件损坏: {exc}") from exc


@app.get("/source/probe")
def probe_source(uri: str, stride: int = 1, fps: float | None = None) -> dict:
    """探测帧源是否可用，返回媒体信息并试读一帧。

    现场接 RTSP / 摄像头之前先跑这个，能省掉大量"为什么连不上"的排查。
    cv2 采用函数内导入：占位模式不装 opencv 也能正常启动。
    """
    from .frame import create_source, detect_kind

    try:
        kind = detect_kind(uri)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        source = create_source(uri, kind=kind, stride=max(1, stride), fps=fps)
    except Exception as exc:  # noqa: BLE001 - 打开失败的形态很杂，统一转 400
        raise HTTPException(status_code=400, detail=f"无法打开帧源: {exc}") from exc

    try:
        meta = source.meta
        first = source.read()
        return {
            "ok": True,
            "kind": meta.kind,
            "uri": meta.uri,
            "fps": meta.fps,
            "width": meta.width,
            "height": meta.height,
            "totalFrames": meta.total_frames,
            "firstFrameReadable": first is not None,
            "firstFrameTs": first.timestamp_ms if first else None,
        }
    finally:
        source.close()


@app.get("/mode")
def get_mode() -> dict:
    return {"mode": mode["value"], "params": PARAMS[mode["value"]], "templates": PARAMS}


@app.post("/mode")
def set_mode(body: ModeRequest) -> dict:
    mode["value"] = body.mode
    return {"mode": mode["value"], "params": PARAMS[mode["value"]], "auto": body.auto}


@app.post("/reset")
def reset() -> dict:
    scorer.reset()
    # 真实检测器持有跟踪状态；场景切换时必须同步清空，否则新目标会沿用旧 track_no
    reset_tracker = getattr(detector, "reset", None)
    if callable(reset_tracker):
        reset_tracker()
    last_infer_at["value"] = 0.0
    return {"reset": True}
