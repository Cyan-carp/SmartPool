<div align="center">

# 智慧泳池 · 溺水实时防护系统

> 推理服务默认以**占位检测器**运行，画面与传感器数据由模拟器合成。接入真实权重与摄像头的完整路径见[检测模型](#检测模型)与[数据与使用边界](#数据与使用边界)。

面向泳池场景的溺水检测、分级预警与处置闭环平台
A drowning-detection, graded-alerting and closed-loop response platform for swimming pools.

<p><i>合成数据演示 · 检测器可切换 · 评估指标全部来自 results.csv</i></p>

[English](#english) | 中文说明

![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-495057?style=flat-square)
![Stack](https://img.shields.io/badge/stack-Vue%203%20%C2%B7%20Spring%20Boot%20%C2%B7%20FastAPI-1c7ed6?style=flat-square)
![Model](https://img.shields.io/badge/model-Mamba--YOLO--T%20%C2%B7%206.0M-7048e8?style=flat-square)
![mAP](https://img.shields.io/badge/mAP%400.5-0.8330-2f9e44?style=flat-square)
![License](https://img.shields.io/badge/license-AGPL--3.0-e8590c?style=flat-square)

</div>

## 这是什么

一个从零写起的泳池安全监测平台：把监控画面接进来，跑人体检测，按位置与停留时间累计风险，触发分级告警，交由值班人员确认处置，全过程留痕可回溯。

它不是单个检测脚本，而是一条完整链路：**取帧 → 检测 → 跟踪 → 评分 → 判警 → 处置 → 复盘**。每个阶段有独立的源码目录，模拟器、推理服务、业务后端与前端控制台各自可独立启动与替换。

系统面向泳池安全管理中三个具体问题：溺水过程安静快速、人工注视难以持续、事故追溯缺少客观依据。检测模型基于以状态空间模型为骨干的 Mamba-YOLO，在保持线性复杂度的前提下建模高分辨率画面中的长程依赖。

> **当前状态**：推理环节运行于占位检测器，所有画面、手环与水质数据由模拟器生成；真实模型的接口与视频链路已实现，需自行准备权重与 GPU 环境后切换。
>
> **数据说明**：仓库内不含数据集与模型权重。检测性能数字取自公开数据集 Roboflow `drowning-detect` v7 的验证集结果，不代表真实场馆表现。

## 主要功能

| 能力 | 说明 |
| --- | --- |
| 实时监控 | 画面叠加检测框、轨迹编号、行为标签与风险分数；分区围栏、在场人数、儿童人数、水质面板同屏展示 |
| 风险分级 | 基础分 + 头部未出水时长 + 静止时长 + 手环生理指标加权，输出正常 / 提示 / 弱告警 / 强告警四级 |
| 告警闭环 | 生成、升级、去重、确认、派单、解除、误报标记全流程；服务端锁存，不因目标恢复而自动消失 |
| 实时推送 | WebSocket 单连接全局复用；帧静默 6 秒判定链路失效并自动重连，顶栏与页面内提示保持同一状态 |
| 电子围栏 | 画面上绘制多边形区域，配置越界与超时规则，支持浅水区 / 深水区 / 儿童区分别设限 |
| 手环联动 | 摄像头目标与手环编号配对，心率、血氧与视觉判定交叉验证，避免单一信号误报 |
| 数据看板 | 区域密度热力图、风险趋势、峰谷人流、告警等级分布；无数据时显示占位说明而非空白 |
| 结果回放 | 加载离线处理结果，按时间轴还原每帧检测框，支持播放 / 暂停 / 逐帧 / 0.5–4 倍速 |
| 实时画面 | MJPEG 推流，支持视频文件 / RTSP / 本地摄像头 / 图片序列四类源；按需推理，无人观看即暂停 |
| 模型与算力 | 检测提供者状态、分时域档位切换、推理延迟曲线；区分"过期"与"无结果" |
| 演示控制台 | 剧本注入（正常游泳 / 静止下沉 / 儿童误闯 / 水质超标）、故障注入、时钟倍速、八步演示主线 |
| 一键部署 | Docker Compose 编排六个容器，Nginx 统一入口，配置文件全部通过环境变量注入 |

## 技术架构

```
模拟数据源（游客轨迹 / 手环 / 水质 / 摄像头状态）
      │  HTTP
      ▼
FastAPI 推理服务
      ├──► 检测器抽象 ── 占位实现（默认） / Mamba-YOLO 实现
      ├──► 帧源抽象 ──── 视频文件 / RTSP / 摄像头 / 图片序列
      ├──► 风险打分 ──── 规则 + 时序累计
      └──► MJPEG 推流 ── 覆盖式帧槽 + 按需推理
      │
      ▼
Spring Boot 业务后端
      ├──► MySQL        告警、围栏、设备、审计
      ├──► Redis        缓存与会话
      └──► WebSocket ──► Vue 3 控制台（10 个业务页面）
      │
      ▼
Nginx :18080（静态资源 / /api 反代后端 / /ai 反代推理服务）
```

| 层 | 选型 |
| --- | --- |
| 前端 | Vue 3.4 · Vite 5 · TypeScript 5.5 · Element Plus 2.8 · ECharts 5.5 · Pinia 2.2 |
| 后端 | JDK 17 · Spring Boot 3 · MyBatis-Plus · WebSocket |
| 推理 | Python 3.11 · FastAPI 0.115 · OpenCV 4.10（推流）· Ultralytics 8.2.29 |
| 训练 | PyTorch 2.7.1 · Mamba-YOLO-T · Selective Scan CUDA 扩展 |
| 数据 | MySQL 8.0 · Redis 7.4 |
| 运维 | Docker Compose · Nginx · PowerShell 运维脚本 |

## 检测模型

模型以 Mamba-YOLO-T 配置为基础，骨干网络用 `SimpleStem` 下采样后串联 18 个 `VSSBlock`，三次 `VisionClueMerge` 完成 P2→P5 的降采样；颈部为 PAFPN，融合节点使用 `XSSBlock`；检测头在 P3/P4/P5 三个尺度输出。

核心模块位于 `training/ultralytics/nn/modules/mamba_yolo.py`：

| 模块 | 作用 |
| --- | --- |
| `SS2D` | 二维四方向选择性扫描，以线性复杂度建立跨区域依赖 |
| `LSBlock` | 局部空间分支，用深度可分离卷积补充状态空间模块缺失的局部归纳偏置 |
| `RGBlock` | 门控前馈分支 |
| `VisionClueMerge` | 分组卷积 + 切片拼接的下采样，减少小目标细节损失 |

结构规模与实验配置：

| 项目 | 数值 |
| --- | --- |
| 参数量 | 5,985,742（约 6.0 M），404 层 |
| 计算量 | 13.2 GFLOPs @ 640×640 |
| 数据集 | Roboflow `drowning-detect` v7（CC BY 4.0），2 类：Drowning / Swimming |
| 训练配置 | 150 epochs · batch 16 · imgsz 640 · Adam · lr0 0.001 · lrf 0.01 · 关闭 AMP |
| 训练环境 | RTX 4090 24GB · PyTorch 2.7.1 + cu118 |

三组实验结果（详见 `training/` 下的训练脚本与提交材料中的 `实验汇总表.csv`）：

| 实验 | 初始化 | 轮次 | 最优轮 | P | R | mAP@0.5 | mAP@0.5:0.95 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mambayolo9 | T 配置 | 150 | 149 | 0.7998 | 0.7933 | **0.8330** | **0.4976** |
| mambayolo18 | T 配置 | 100 | 97 | 0.7728 | 0.7610 | 0.8122 | 0.4798 |
| mambayolo10 | m9 末轮权重 | 10 | 8 | 0.8187 | 0.7111 | 0.8057 | 0.4478 |

> 续训实验未提升，原因是学习率从收敛后的 1.99×10⁻⁵ 重新回到 0.001，破坏了已收敛的解。断点续训应保留优化器状态与调度进度，或以更小的初始学习率微调。

## 快速开始

### 前置条件

| 依赖 | 版本 | 用途 |
| --- | --- | --- |
| Docker | 20.10+ | 全部服务容器化运行 |
| PowerShell | 5.1 或 7 | 运维脚本 |
| Node.js | 20.19+ 或 22.12+ | 仅前端本地开发需要 |
| JDK | 17+ | 仅后端本地开发需要 |
| NVIDIA 驱动 + CUDA | 12.1 | 仅接入真实模型推理需要 |

### 一键启动

```powershell
# 1. 克隆并准备配置（.env 已被 Git 忽略）
git clone <repository-url> SmartPool
cd SmartPool
Copy-Item deploy/.env.example deploy/.env
# 至少修改 MYSQL_PASSWORD 与 JWT_SECRET，或直接执行下一步由脚本自动生成

# 2. 构建并启动全部服务
cd deploy
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\up.ps1

# 3. 浏览器访问
#    http://127.0.0.1:18080
```

首次启动约需 3–5 分钟（拉取镜像 + 构建前端与后端）。启动后六个容器状态应为 `healthy`。

### 登录账号

| 账号 | 角色 | 可见范围 |
| --- | --- | --- |
| `lifeguard` | 救生员 | 实时监控、告警处置、手环 |
| `manager` | 值班管理员 | 全部业务页面 |
| `sysadmin` | 系统管理员 | 全部页面 + 模型与算力、演示控制台 |

初始口令见 `stages/02-backend` 的初始化脚本；如已修改请以实际配置为准。

### 接入真实模型

```powershell
# 1. 在有 GPU 的机器上准备环境
cd training
pip install torch==2.7.1 torchvision --index-url https://download.pytorch.org/whl/cu118
pip install seaborn thop timm einops pyyaml
cd selective_scan && pip install -v --no-cache-dir --force-reinstall . && cd ..
pip install -v -e .

# 2. 训练或使用已有权重
python mbyolo_train.py --task train --data ./Drowning/data.yaml `
  --config ultralytics/cfg/models/mamba-yolo/Mamba-YOLO-T.yaml `
  --epochs 150 --batch_size 16 --optimizer Adam --lr0 0.001 --name mambayolo9

# 3. 回到部署目录切换检测器
#    编辑 deploy/.env：
#    AI_DETECTOR_PROVIDER=mamba-yolo
#    AI_MODEL_PATH=/app/weights/best.pt
#    AI_DEVICE=cuda
```

推理服务需要额外安装 `stages/03-ai-service/requirements-ml.txt`，并确保 `selective_scan` 与容器内 CUDA 版本匹配。若部署机无 GPU，推荐使用离线预生成路径（见下节）。

### 离线预生成与回放

无 GPU 环境下可先在别处跑完一段录像，把结果落成 JSON，前端按时间轴回放：

```powershell
cd stages/03-ai-service
python tools/pregenerate.py --source ./demo.mp4 --provider mamba-yolo `
  --model ./best.pt --device cuda --stride 5 --out ./artifacts/demo.json
docker cp ./artifacts/demo.json smartpool-ai:/app/artifacts/
```

前端「结果回放」页选择该文件即可。回放帧率按 `源帧率 / 抽帧间隔` 还原，与真实时间轴一致。

## 常用命令

以下命令在仓库根目录执行。

| 目的 | 命令 |
| --- | --- |
| 启动全部服务 | `cd deploy; .\scripts\up.ps1` |
| 查看状态 | `docker compose -f deploy/compose.yaml ps` |
| 查看推理服务日志 | `docker logs -f smartpool-ai` |
| 停止服务（保留数据） | `cd deploy; .\scripts\down.ps1` |
| 前端类型检查 | `npm --prefix stages/04-frontend run typecheck` |
| 前端构建 | `npm --prefix stages/04-frontend run build` |
| 后端打包 | `mvn -f stages/02-backend/pom.xml package -DskipTests` |
| 探测视频源 | `curl "http://127.0.0.1:18080/ai/source/probe?uri=rtsp://..."` |
| 查看推流状态 | `curl http://127.0.0.1:18080/ai/stream/status` |

## 疑难解答

| 现象 | 处理 |
| --- | --- |
| 页面打开空白，接口 404 | 后端未就绪。先 `curl http://127.0.0.1:18080/api/v1/health`，再查 `docker logs smartpool-backend` |
| 顶栏"实时链路 断开"一直不恢复 | WebSocket 未连通。检查 Nginx 是否转发 `/ws`，以及浏览器是否拦截了连接 |
| 图表区域全空 | 该时段无数据，页面会显示"暂无…"占位；确认模拟器容器在运行 |
| 推理服务反复重启 | 多为依赖缺失。`docker logs smartpool-ai` 查看首个异常，常见是 `python-multipart` 未装 |
| `/ai/stream.mjpg` 返回 503 | 未配置 `AI_VIDEO_SOURCE`。设置后重启 `smartpool-ai` |
| 实时画面有画面但没有框 | 检测器为占位实现，不产生检测框。切换 `AI_DETECTOR_PROVIDER=mamba-yolo` 并准备权重 |
| MJPEG 首帧迟迟不出来 | 反向代理开启了缓冲。确认 `stages/04-frontend/nginx.conf` 中 `/ai/` 路由已设 `proxy_buffering off` |
| 回放列表为空 | 回放 JSON 未拷入容器。`docker cp xxx.json smartpool-ai:/app/artifacts/` 后刷新 |
| 中文路径下脚本失败 | 把仓库放到纯 ASCII 路径，或改用已装好依赖的解释器 |
| 端口 18080 被占用 | 修改 `deploy/compose.yaml` 中 nginx 的端口映射 |

## 开发文档

`notes/` 下是完整的设计与开发记录，按主题分册：

| 想做什么 | 从哪里进 |
| --- | --- |
| 先了解系统全貌 | [项目笔记总入口](notes/00-项目笔记总入口.md) |
| 查当前运行状态与已知限制 | [当前系统状态](notes/00-当前系统状态.md) |
| 弄清目录为什么这样分 | [项目目录导航](notes/00-项目目录导航.md) |
| 把平台用起来 | [系统使用与运维手册](notes/03-系统使用与运维手册/) |
| 改前端页面 | [前端说明](stages/04-frontend/README.md) |
| 改后端接口 | [后端说明](stages/02-backend/README.md) |
| 接入真实模型或摄像头 | [推理服务说明](stages/03-ai-service/README.md) |
| 调整模拟剧本 | [模拟器说明](stages/01-simulator/README.md) |
| 告警分发与推送 | [告警分发说明](stages/05-alerting/README.md) |
| 部署、回滚与变更记录 | [部署发布记录](notes/04-部署发布与变更记录/) · [deploy/](deploy/) |

## 数据与使用边界

**仓库公开的是源码、配置模板与设计文档。** 以下内容不随 Git 提供，需自行准备：

- **数据集**：`drowning-detect` v7 来自 Roboflow（CC BY 4.0），需自行下载并修改 `training/data.yaml` 中的路径
- **模型权重**：`best.pt` 约 35 MB（含优化器状态），建议通过 Release 分发或自行训练
- **回放结果**：`artifacts/` 下的 JSON 为运行产物，不入库
- **私密配置**：`deploy/.env`、数据库卷、证书文件

**关于演示数据**：仓库内所有画面、手环读数、水质参数与告警均由 `stages/01-simulator` 合成。任何基于这些数据的结论都不构成真实泳池的安全依据。

**关于模型指标**：mAP 数字来自公开数据集验证集，训练与验证分布一致；真实场馆在拍摄角度、光照、水质、人群密度上与数据集存在差异，实际表现需实地评估。

**关于姿态**：本项目做的是「溺水 / 游泳」两类目标检测，输出人体框与类别，**不含人体关键点**。系统内的 `posture` 字段由类别粗映射得到，是行为标签而非姿态识别结果。

**关于实时链路**：MJPEG 推流的架构参考了作者此前独立开发的人脸识别考勤系统，针对泳池场景重新实现。两个项目为独立仓库，无代码依赖。

## 许可

本仓库整体以 **AGPL-3.0** 发布，原因是 `training/` 目录包含基于 [Ultralytics](https://github.com/ultralytics/ultralytics)（AGPL-3.0）改造的检测框架代码，需遵循其许可条款。

`stages/` 下的系统平台代码为原创实现，如需以更宽松的条款使用，可单独联系作者。引用本项目的方法或代码时，请注明出处。

```
Copyright (C) 2026 CXXL2026087 项目组

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
```

## 目录

- [这是什么](#这是什么)
- [主要功能](#主要功能)
- [技术架构](#技术架构)
- [检测模型](#检测模型)
- [快速开始](#快速开始)
- [常用命令](#常用命令)
- [疑难解答](#疑难解答)
- [开发文档](#开发文档)
- [数据与使用边界](#数据与使用边界)
- [许可](#许可)
- [English](#english)

```
SmartPool/
├── stages/                      系统平台，五个子系统
│   ├── 01-simulator/            模拟数据源（游客轨迹、手环、水质、摄像头状态）
│   ├── 02-backend/              Spring Boot 业务后端（15 个业务包）
│   ├── 03-ai-service/           FastAPI 推理服务（检测器、帧源、推流、预生成）
│   ├── 04-frontend/             Vue 3 控制台（10 个业务页面）
│   └── 05-alerting/             告警分发
├── training/                    检测模型训练代码
│   ├── ultralytics/             改造后的检测框架（Mamba 模块、模型配置、引擎）
│   ├── selective_scan/          Selective Scan CUDA 扩展
│   ├── tools/                   训练与评估辅助脚本
│   ├── mbyolo_train.py          训练入口
│   ├── test_mbyolo.py           验证 / 推理入口
│   └── data.yaml                数据集定义
├── deploy/                      Docker Compose 编排与运维脚本
├── notes/                       设计与开发记录（81 篇）
└── artifacts/                   运行产物（不入库）
```

## English

**SmartPool** is a drowning-detection and alerting platform for swimming pools, built end to end: frame ingestion, object detection, tracking, risk scoring, graded alerting, human acknowledgement, and event review.

A simulated data source feeds people tracks, wristband vitals and water-quality readings into a FastAPI inference service, which runs a pluggable detector (placeholder by default, Mamba-YOLO when weights are provided), scores risk from stillness and submersion time, and pushes results over WebSocket to a Vue 3 console backed by Spring Boot, MySQL and Redis.

**Highlights**

- End-to-end chain: capture → detect → track → score → alert → respond → review
- Mamba-YOLO-T backbone, 6.0 M parameters, mAP@0.5 = 0.8330 on the public `drowning-detect` v7 dataset
- Pluggable detector and frame source: placeholder / real weights, video file / RTSP / camera / image sequence
- MJPEG streaming with a latest-frame slot and viewer-counted inference — no GPU burn when nobody is watching
- Single global WebSocket with 6-second silence detection and automatic reconnection
- Graded alerts latched on the server: they persist until a human acknowledges them, with a full response timeline
- Ten console pages covering monitoring, alert handling, replay, geofencing, wristbands, dashboards, devices and a demo console

**Status**

The inference stage runs a placeholder detector; all imagery, wristband and water-quality data are synthetic. The real model interface and the video pipeline are implemented and tested, but no weights ship with this repository. Metrics come from the validation split of a public dataset and do not represent real-pool performance.

This is a two-class object detection task (`Drowning` / `Swimming`); no human keypoints are produced. The `posture` field is a coarse label derived from the predicted class.

**License**

AGPL-3.0, because `training/` contains a modified fork of Ultralytics. The `stages/` platform code is original work.
