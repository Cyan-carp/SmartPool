"""离线预生成检测结果：视频 -> JSON。

为什么需要它
------------
部署机（home-dev）没有 GPU，实时跑 Mamba-YOLO 带不动大屏。
可行做法是先在任意有 GPU 的机器上把一段录像整段跑完，把每帧结果落成 JSON；
演示时前端按时间轴回放即可，帧率稳定、可复现，不会出现"现场演不出来"。

这份 JSON 同时是结题材料的原始证据：它记录了用的是哪个权重、什么参数、
哪段视频，每个目标的框和置信度都能追溯。

用法
----
  # 有 GPU + 权重：跑真实模型
  python tools/pregenerate.py --source ./demo.mp4 --provider mamba-yolo \
      --model /path/mambayolo9/weights/best.pt --device cuda \
      --stride 5 --out ./artifacts/demo.json

  # 没有权重时先验证链路（占位检测器不认图像，只会返回空结果，仅用于打通流程）
  python tools/pregenerate.py --source ./frames --provider mock --max-frames 20

  # 只采样不落盘，用于确认视频能正常解码
  python tools/pregenerate.py --source ./demo.mp4 --provider mamba-yolo \
      --model best.pt --dry-run --max-frames 10
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# 允许从仓库内直接执行（python tools/pregenerate.py）
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.detector.mamba_yolo import MambaYoloDetector  # noqa: E402
from app.detector.mock import MockDetector  # noqa: E402
from app.frame import create_source  # noqa: E402
from app.pipeline import iter_detections  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="离线预生成检测结果 JSON")
    parser.add_argument("--source", required=True, help="视频文件 / RTSP / 摄像头索引 / 图片目录")
    parser.add_argument("--kind", default=None, choices=["file", "rtsp", "camera", "image_seq"])
    parser.add_argument("--provider", default="mamba-yolo", choices=["mamba-yolo", "mock"])
    parser.add_argument("--model", default=None, help="权重路径（provider=mamba-yolo 必填）")
    parser.add_argument("--device", default="cpu", help="cuda / cpu")
    parser.add_argument("--stride", type=int, default=5, help="每 N 帧取 1 帧")
    parser.add_argument("--fps", type=float, default=None, help="覆盖帧率（摄像头常返回 0）")
    parser.add_argument("--max-frames", type=int, default=0, help="最多输出多少帧，0 为不限")
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--loop", action="store_true", help="读完循环（仅文件与图片序列）")
    parser.add_argument("--out", default=None, help="输出 JSON 路径")
    parser.add_argument("--progress-every", type=int, default=50)
    parser.add_argument("--dry-run", action="store_true", help="只跑不写文件")
    return parser.parse_args()


def build_detector(provider: str, model_path: str | None, device: str):
    if provider == "mock":
        detector = MockDetector()
        detector.load(None, device)
        return detector
    detector = MambaYoloDetector()
    detector.load(model_path, device)
    return detector


def main() -> int:
    args = parse_args()

    if args.provider == "mamba-yolo" and not args.model:
        print("错误：provider=mamba-yolo 需要 --model 指定权重路径", file=sys.stderr)
        return 2

    detector = build_detector(args.provider, args.model, args.device)
    source = create_source(
        args.source,
        kind=args.kind,
        stride=args.stride,
        loop=args.loop,
        fps=args.fps,
        max_frames=args.max_frames,
    )

    meta = source.meta
    print(
        f"[pregenerate] source kind={meta.kind} fps={meta.fps} "
        f"size={meta.width}x{meta.height} total={meta.total_frames} stride={args.stride}",
        file=sys.stderr,
    )

    def on_progress(produced: int, record) -> None:
        print(
            f"[pregenerate] {produced} frames | last: ts={record.timestamp_ms}ms "
            f"targets={len(record.detections)} infer={record.infer_ms}ms",
            file=sys.stderr,
        )

    frames: list[dict] = []
    total_targets = 0
    try:
        for record in iter_detections(
            source,
            detector,
            conf=args.conf,
            imgsz=args.imgsz,
            max_frames=args.max_frames,
            on_progress=on_progress,
            progress_every=args.progress_every,
        ):
            frames.append(record.to_dict())
            total_targets += len(record.detections)
    finally:
        source.close()

    if not frames:
        print("未产生任何帧：请检查视频源是否可解码，或调小 --stride", file=sys.stderr)
        return 1

    avg_infer = round(sum(item["inferMs"] for item in frames) / len(frames), 2)
    payload = {
        "version": 1,
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "provider": args.provider,
        "modelLoaded": detector.model_loaded,
        "modelPath": args.model,
        "device": args.device,
        "params": {
            "conf": args.conf,
            "imgsz": args.imgsz,
            "stride": args.stride,
        },
        "source": {
            "kind": meta.kind,
            "uri": meta.uri,
            "fps": meta.fps,
            "width": meta.width,
            "height": meta.height,
            "totalFrames": meta.total_frames,
            "loop": meta.loop,
        },
        "summary": {
            "frames": len(frames),
            "targets": total_targets,
            "avgInferMs": avg_infer,
        },
        "frames": frames,
    }

    print(
        f"[pregenerate] 完成 frames={len(frames)} targets={total_targets} "
        f"avgInfer={avg_infer}ms modelLoaded={detector.model_loaded}",
        file=sys.stderr,
    )

    if args.dry_run:
        print("[pregenerate] --dry-run 已开启，未写入文件", file=sys.stderr)
        return 0

    out_path = Path(args.out) if args.out else Path("artifacts") / f"video-{datetime.now():%Y%m%d-%H%M%S}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[pregenerate] 已写入 {out_path}  ({out_path.stat().st_size / 1024:.1f} KB)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
