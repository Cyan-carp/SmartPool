# 03 · 推理服务（ai-service）

> 职责：帧级检测 → 跟踪号 → 时序风险打分 → 上报风险事件。
> 状态：**M1 已实现**（容器 `smartpool-ai`，端口 8000，仅 compose 网络内）。
> 当前模型：**空置**，使用 `MockDetector`，`modelLoaded=false`，输出带 `placeholder=true`。

## 抽象设计

```python
class Detector(ABC):
    @abstractmethod
    def load(self, model_path: str | None, device: str) -> None: ...

    @abstractmethod
    def infer(self, frame: Frame, ctx: SceneContext) -> list[Detection]: ...
```

| 实现 | 用途 | 状态 |
| --- | --- | --- |
| `MockDetector` | 按剧本与真实位置生成带噪声的框与姿态 | M1 |
| `MambaYoloDetector` | 真实权重推理 | 待模型就绪 |

- `Tracker`：演示版用简化 IOU + 最近邻分配稳定 `track_id`；将来替换 DeepSORT，接口不变。
- `RiskScorer`：规则（头部未出水时长、静止时长）+ 窗口打分，输出 0–1 风险分。
- 所有输出带 `placeholder` 标记（占位时 `true`）。

## 计划目录

```text
03-ai-service/
├── README.md
├── app/
│   ├── main.py           FastAPI 入口
│   ├── detector/         base.py / mock.py / mamba_yolo.py(待)
│   ├── tracker/          simple_iou.py
│   ├── risk/             scorer.py, rules.py
│   ├── scenarios/        engine.py
│   └── schemas.py        Pydantic 契约
├── scenarios/            剧本 JSON（与 simulator 共享格式）
├── tests/                pytest
└── requirements.txt
```

## 已实现接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 提供者、是否加载权重、模式、模拟源可达性 |
| POST | `/infer?poolId=` | 取世界快照 → 检测 → 打分，返回帧数据 |
| GET/POST | `/mode` | 查看/切换 PEAK 与 OFFPEAK 参数模板 |
| POST | `/reset` | 清空风险窗口 |

风险判定的阈值口径（头部未出水 20s 满档、静止 25s 满档、强告警 0.80）见
[演示数据与模型占位边界](../../notes/02-工程规范边界与验收治理/项目工程规范/05-演示数据与模型占位边界.md)。

## 运行

```powershell
cd deploy\scripts
.\logs.ps1 -Service ai
```

容器内查看判定结果：

```powershell
docker --context home-dev exec smartpool-ai python -c "import urllib.request,json;d=json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8000/infer?poolId=1',method='POST')));print([(t['trackNo'],t['level'],t['riskScore']) for t in d['targets']])"
```

触发剧本后再次执行，可看到指定目标升到 `STRONG`：

```powershell
docker --context home-dev exec smartpool-ai python -c "import urllib.request;urllib.request.urlopen(urllib.request.Request('http://simulator:8010/sim/scenario/drown_still',method='POST'))"
```

## 替换真实模型的步骤

`detector/mamba_yolo.py` 已提供骨架实现，接入只需配置，不改上层代码：

1. 安装 ML 依赖：`pip install -r requirements-ml.txt`
2. 配置环境变量：
   - `AI_DETECTOR_PROVIDER=mamba-yolo`
   - `AI_MODEL_PATH=/path/to/mambayolo9/weights/best.pt`
   - `AI_DEVICE=cuda`（无 GPU 时填 `cpu`，可以跑通但很慢）
3. 重启服务，`GET /health` 应返回 `modelLoaded: true`、`placeholder: false`。
4. 用 `POST /infer/image` 上传一张泳池测试图，确认 `targets` 有框、
   类别为 `Drowning` / `Swimming`，坐标系为 0~1 归一化。
5. 后端与前端无需改动：`placeholder`、`synthetic` 已按真实状态返回。

## 视频取帧

`app/frame/` 把四类数据源收敛到同一个 `FrameSource` 接口，换源只改配置不改代码：

| 类型 | uri 示例 | 典型用途 |
| --- | --- | --- |
| 视频文件 | `./demo.mp4` | 调试、离线预生成 |
| RTSP | `rtsp://user:pass@host:554/stream1` | 现场摄像头 |
| 摄像头 | `0` | 本机 USB 摄像头 |
| 图片序列 | `./frames/` | 数据集 test 图，零成本验证链路 |

```python
from app.frame import create_source
from app.pipeline import iter_detections

with create_source("./demo.mp4", stride=5, loop=True) as source:   # 每 5 帧取 1 帧
    for record in iter_detections(source, detector, conf=0.25):
        print(record.frame_index, record.timestamp_ms, len(record.detections))
```

抽帧用 `stride`：泳池 25fps 的相邻帧几乎无差异，按 5 抽 1 即 5fps，
足够做风险判定，推理负载降到 1/5。

**接现场前先探测**，能省掉大量"为什么连不上"的排查：

```bash
curl "http://127.0.0.1:8000/source/probe?uri=rtsp://192.168.1.10:554/stream1&stride=5"
# {"ok":true,"kind":"rtsp","fps":25.0,"width":1920,"height":1080,
#  "firstFrameReadable":true,"firstFrameTs":0.0}
```

## 离线预生成（部署机无 GPU 时的推荐路径）

部署主机没有 NVIDIA 驱动，CPU 跑 Mamba-YOLO 带不动大屏。可行做法是
先在任意有 GPU 的机器上把一段录像整段跑完，逐帧结果落成 JSON，
演示时前端按时间轴回放——帧率稳定、可复现，不会出现"现场演不出来"。

```bash
python tools/pregenerate.py --source ./demo.mp4 --provider mamba-yolo \
    --model /path/mambayolo9/weights/best.pt --device cuda \
    --stride 5 --out ./artifacts/demo.json
```

输出结构：`source`（媒体信息）+ `params`（conf/imgsz/stride）+ `summary`
（帧数、目标数、平均推理耗时）+ `frames[]`（每帧 ts、inferMs、targets）。
`provider=mock` 时不会产生检测框，仅用于打通链路。

这份 JSON 同时是结题材料的原始证据：权重路径、参数、视频来源都可追溯。

## 实时推流（MJPEG）

`GET /stream.mjpg` 输出 `multipart/x-mixed-replace`，前端 `<img src>` 直接播放，
不需要 WebSocket，也不需要前端解码 JPEG。

设计沿自已落地的人脸识别项目：

- **覆盖式帧槽**：只保留最新一帧，慢客户端自动丢帧，永不积压内存
- **按需推理**：viewer 归零时暂停采集与推理，没人看就不烧算力
- **画面自带标注**：左上角强制叠加 `[PLACEHOLDER]` 或 `[LIVE]`，
  避免占位输出被误认为真实检测效果

启用方式（compose 环境变量）：

```bash
AI_VIDEO_SOURCE=/app/artifacts/demo.mp4   # 或 rtsp://... 、或 0（摄像头索引）
AI_VIDEO_STRIDE=5                          # 每 5 帧取 1 帧
AI_STREAM_MAX_WIDTH=960                    # 超过该宽度会等比缩小
```

文件与图片序列会按源帧率节流（否则会全速播放成"快进"），RTSP 与摄像头本身实时，不限速。

```bash
curl http://127.0.0.1:18080/ai/stream/status
# {"enabled":true,"viewers":1,"fps":24.8,"lastTargets":3,"modelLoaded":false,...}
```

未配置时返回 503，前端提示"未配置真实视频源"并保持合成画面，不影响原演示流程。

⚠️ HUD 只能用 ASCII：OpenCV 的 Hershey 字体没有中文字形，直接画中文会输出一排问号。
中文说明交给前端 HTML 叠加层。

## 结果回放

`tools/pregenerate.py` 产出的 JSON 放进 `AI_REPLAY_DIR`（容器内 `/app/artifacts`），
前端「结果回放」页按时间轴还原每帧检测框。

```bash
# 拷进容器。挂载在此不可行：从本地 --context 执行 compose 时，
# 相对卷路径会按本地文件系统解析，远程 daemon 找不到
docker --context home-dev cp ./artifacts/xxx.json smartpool-ai:/app/artifacts/
```

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/replay/list` | 列出可回放文件（帧数、目标数、生成时间、来源） |
| GET | `/replay/{name}` | 读取单个回放 JSON（文件名白名单校验，防路径穿越） |

前端页面在侧栏「结果回放」：播放/暂停、逐帧、进度条、0.5x–4x 倍速。
回放帧率 = `source.fps / params.stride`，与真实时间轴一致。

### 骨架留白（按现场条件补）

- **跟踪**：`_IouTracker` 只是简化的 IoU 关联，保证 `track_no` 在帧间稳定，
  让 RiskScorer 能累计静止时长。正式版应换 ByteTrack
  （`ultralytics` 内置 `bytetrack.yaml`），直接用 `result.boxes.id` 即可。
- **姿态**：模型是「溺水 / 游泳」二分类检测，`posture` 由类别粗映射
  （Drowning→underwater_still，Swimming→swimming），**不是关键点姿态**。
  对外表述统一为"溺水分级判定"。
- **实时链路**：`/infer` 目前仍读模拟器世界状态。接真实摄像头还需把
  `FrameSource` 接进 `LiveFeedService` 的推送循环，属于本次未动的范围。

### 部署环境注意

`selective_scan` 是编译型 CUDA 扩展，必须与 torch / CUDA 版本匹配。
当前 Dockerfile 基于 `python:3.11-slim`，**无法编译该扩展**；
跑真实模型需改用 `nvidia/cuda` 基础镜像并在构建时编译 `selective_scan`，
或把推理服务单独部署在训练用的 GPU 机器上，其余服务保持容器化。

权重来源、验证范围与验证日期仍需在笔记里登记。

细则见 [演示数据与模型占位边界](../../notes/02-工程规范边界与验收治理/项目工程规范/05-演示数据与模型占位边界.md)。

## 相关文档

- [接口契约](../../notes/01-项目调研规划与开发建设记录/01-第一版-演示平台/03-架构设计/02-接口契约.md)
- [总体架构](../../notes/01-项目调研规划与开发建设记录/01-第一版-演示平台/03-架构设计/01-总体架构与数据流.md)
