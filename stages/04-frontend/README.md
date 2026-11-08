# 04 · 前端控制台（frontend）

> 职责：把检测与告警变成人能一眼看懂的画面。
> 状态：**M1 已实现骨架**（登录、布局、8 个页面、大屏实时渲染；构建产物由 `smartpool-nginx` 托管）。

## 技术栈

Vue 3 · Vite 5 · TypeScript 5 · Element Plus · ECharts 5 · Pinia · Axios · 原生 WebSocket 封装

## 计划目录

```text
04-frontend/
├── README.md
├── package.json
├── vite.config.ts          /api 与 /ws 代理到 :8080
├── src/
│   ├── main.ts
│   ├── App.vue
│   ├── router/             路由与角色守卫
│   ├── stores/             user / live / alert / demo
│   ├── api/                axios 实例与各模块 api
│   ├── ws/                 连接、心跳、重连、消息分发
│   ├── types/              与契约一致的 TS 类型
│   ├── composables/        useClock / useCanvasPool / useRiskColor
│   ├── components/
│   │   ├── pool-canvas/    底图、精灵、叠加层（分层 Canvas）
│   │   ├── alert/          告警卡、时间线
│   │   ├── chart/          ECharts 封装
│   │   └── common/
│   └── views/
│       ├── login/
│       ├── monitor/        监控大屏（P0）
│       ├── alerts/         告警中心与详情（P0）
│       ├── replay/         事件回溯（P0）
│       ├── zones/          电子围栏（P0）
│       ├── dashboard/      数据看板（P0）
│       ├── devices/        设备与水质（P0）
│       ├── model/          模型与算力调度（P0）
│       └── demo/           演示控制台（P0）
├── tests/                  Vitest
└── index.html
```

## 运行

生产形态（推荐）：由 `deploy/compose.yaml` 构建进 Nginx，本地起隧道后访问 `http://127.0.0.1:18080`。

```powershell
cd deploy\scripts
.\tunnel.ps1
```

本地开发（热更新）：先保持隧道，再指向隧道端口：

```powershell
cd stages\04-frontend
npm install
$env:VITE_API_TARGET = 'http://127.0.0.1:18080'
npm run dev        # http://127.0.0.1:5173
```

## 页面与实现状态

| 路由 | 页面 | M1 状态 |
| --- | --- | --- |
| `/login` | 登录 | 可用，四角色菜单不同 |
| `/monitor` | 实时监控 | Canvas 绘制池体/区域/检测框，WS 实时刷新，风险目标列表 |
| `/alerts` | 告警中心 | 空列表骨架（M3） |
| `/replay` | 事件回溯 | 占位（M3） |
| `/zones` | 电子围栏 | 只读列表（M4 支持绘制） |
| `/dashboard` | 数据看板 | 实时计数卡片（M4 上图表） |
| `/devices` | 设备与水质 | 摄像头表 + 水质数值（M5 扩指标） |
| `/model` | 模型与算力 | 提供者、占位标记、两档参数 |
| `/demo` | 演示控制台 | 剧本说明（M6 开放注入） |

## 构建注意

- 控制台与构建均需 Node 20；镜像内使用 `registry.npmmirror.com`。
- 全局按需引入未做（`element-plus` 全量引入，产物约 1.1 MB gzip 后 373 KB），M6 再做按需拆分。

## 关键约定

- **合成画面分层**：底层泳池与区域（离屏缓存）、中层泳者精灵、上层检测框与标签；只重绘脏区。
- **坐标**：所有绘制用归一化坐标乘画布尺寸，禁止混用 CSS 像素。
- **时间**：插值基准用服务端 `ts`，不用 `Date.now()`。
- **占位标记**：涉及模型结论的位置显示「占位模式」徽标。
- **枚举容错**：未知值降级为 `unknown` 并记录一条前端日志，不白屏。
- **类型**：接口类型统一在 `types/`，页面不手写字段名字面量。

## 相关文档

- [接口契约](../../notes/01-项目调研规划与开发建设记录/01-第一版-演示平台/03-架构设计/02-接口契约.md)
- [总体架构](../../notes/01-项目调研规划与开发建设记录/01-第一版-演示平台/03-架构设计/01-总体架构与数据流.md)
- [代码分支与提交规范](../../notes/02-工程规范边界与验收治理/项目工程规范/02-代码分支与提交规范.md)
