---
tags: [智慧泳池, 代码导航]
status: 现行
scope: 第一版
updated: 2026-11-05
---

# 代理页 · 后端

> 指向 [stages/02-backend](../../stages/02-backend/README.md)。

- **职责**：业务唯一事实源——鉴权、泳池与区域、告警状态机、处置、审计、统计、WebSocket 广播。
- **技术**：Spring Boot 3 + MyBatis-Plus + MySQL 8.0 + Redis 7 + Spring Security(JWT)。
- **分层**：`controller / service / mapper / domain / config`。
- **启动命令**：见该目录 README（M1 落地后补全）。
- **相关设计**：[[01-项目调研规划与开发建设记录/01-第一版-演示平台/03-架构设计/02-接口契约]]、[[01-项目调研规划与开发建设记录/01-第一版-演示平台/03-架构设计/03-数据模型]]

## 相关笔记

- [[05-代码工作区导航与链接映射/00-索引·代码工作区导航]]
