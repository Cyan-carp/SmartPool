---
tags: [智慧泳池, 代码导航]
status: 现行
scope: 第一版
updated: 2026-11-05
---

# 代理页 · 推理服务（占位）

> 指向 [stages/03-ai-service](../../stages/03-ai-service/README.md)。

- **职责**：帧级检测、跟踪号分配、时序风险打分，对外上报风险事件。
- **当前状态**：`MockDetector` 占位，`modelLoaded=false`，不加载真实权重。
- **替换点**：实现 `Detector` 接口的 `MambaYoloDetector`，改 `AI_DETECTOR_PROVIDER`，见 [[02-工程规范边界与验收治理/项目工程规范/05-演示数据与模型占位边界]]。
- **技术**：Python 3.11 + FastAPI + OpenCV。
- **相关设计**：[[01-项目调研规划与开发建设记录/01-第一版-演示平台/03-架构设计/02-接口契约]]

## 相关笔记

- [[05-代码工作区导航与链接映射/00-索引·代码工作区导航]]
