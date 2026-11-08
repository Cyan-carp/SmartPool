# 02 · 后端（backend）

> 职责：业务唯一事实源——鉴权、泳池与区域、告警状态机、处置流程、审计、统计、WebSocket 广播。
> 状态：**M1 已实现骨架**（容器 `smartpool-backend`，端口 8080，未对外发布）。

## 技术栈

Spring Boot 3.2 · MyBatis-Plus · MySQL 8.0 · Redis 7(Lettuce) · Spring Security + JWT · WebSocket · Flyway

## 计划目录

```text
02-backend/
├── README.md
├── pom.xml
├── src/main/java/com/smartpool/
│   ├── SmartPoolApplication.java
│   ├── common/        统一包络、异常、错误码、traceId
│   ├── security/      JWT、RBAC、密码编码
│   ├── auth/          登录、当前用户
│   ├── pool/          泳池、摄像头、区域围栏
│   ├── live/          快照、轨迹查询
│   ├── alert/         告警状态机、去重升级、处置
│   ├── event/         事件片段、导出任务
│   ├── device/        设备、维护、水质
│   ├── model/         模型信息、档位参数、指标
│   ├── stats/         概览、热力图、趋势、峰谷
│   ├── demo/          剧本注入、时钟、故障、重置
│   └── ws/            WebSocket 会话与广播
├── src/main/resources/
│   ├── application.yml
│   └── db/migration/  Flyway V1__init.sql …
└── src/test/java/     JUnit 5 + MockMvc
```

## 已实现接口（M1）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 健康检查（含占位模型标记） |
| POST | `/api/v1/auth/login` | 登录，返回 JWT |
| GET | `/api/v1/auth/me` | 当前用户与角色菜单 |
| POST | `/api/v1/auth/logout` | 无状态登出 |
| GET | `/api/v1/pools` · `/pools/{id}` | 泳池 |
| GET | `/api/v1/cameras?poolId=` | 摄像头 |
| GET | `/api/v1/zones?poolId=` | 区域与围栏多边形 |
| GET | `/api/v1/live/snapshot?poolId=` | 实时快照（内存 + Redis 缓存） |
| GET | `/api/v1/alerts` | 空列表骨架（M3 实现状态机） |
| GET | `/api/v1/model/info` · `/model/params` | 模型与档位参数（标注占位） |
| WS | `/ws/live?token=` | 实时推送 `system.notice` / `frames` |

## 运行

由 `deploy/compose.yaml` 托管（MySQL + Redis + 推理服务为依赖）：

```powershell
cd deploy\scripts
.\up.ps1 -SkipSync -NoBuild
.\logs.ps1 -Service backend
```

数据库迁移由 Flyway 自动执行（`src/main/resources/db/migration/V1__init.sql`、`V2__seed.sql`）；
种子用户口令在首次启动时由 `UserInitializer` 升级为 BCrypt。

本地裸跑：需要本机 JDK 17 与可连的 MySQL/Redis，`mvn spring-boot:run`，环境变量见根 `.env.example`。

## 关键约定

- 控制器只做参数校验与调用；SQL 只在 mapper。
- 所有写操作返回受影响资源；非法状态流转返回 `40900`。
- 告警状态机是演示可信度核心：任何「直接改库」都视为未完成。
- WebSocket 只推送，不承担查询；重连后由前端拉 `/live/snapshot` 对齐。
- 每个写操作记 `audit_log`（告警处置、围栏修改、参数变更、导出）。

## 接口与模型

- [接口契约](../../notes/01-项目调研规划与开发建设记录/01-第一版-演示平台/03-架构设计/02-接口契约.md)
- [数据模型](../../notes/01-项目调研规划与开发建设记录/01-第一版-演示平台/03-架构设计/03-数据模型.md)
- [接口联调规范](../../notes/02-工程规范边界与验收治理/项目工程规范/03-接口契约与前后端联调规范.md)
