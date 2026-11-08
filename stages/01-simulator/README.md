# 01 · 模拟数据源（simulator）

> 职责：生成泳池里的「世界」——游客、位置轨迹、姿态、手环生理、水质、设备状态，并按剧本注入事件。
> 状态：**M1 已实现**，容器 `smartpool-simulator`，端口 8010（仅 compose 网络内）。

## 负责什么

| 输出 | 说明 |
| --- | --- |
| 游客与轨迹 | N 名游客在泳池平面内游动，输出归一化坐标与姿态 |
| 手环生理 | 心率、血氧、静止时长，基线 + 扰动 |
| 水质 | 水温、浑浊度、pH、余氯，基线 ± 噪声，可注入超标 |
| 设备状态 | 摄像头在线、镜头清洁度、防水密封、供电 |
| 剧本事件 | 按时间线改变个体行为（停留、下沉、越界、离场） |

## 不负责什么

- 不做风险判定（推理服务做）。
- 不写业务库（后端做）。
- 不做权限与审计。

## 计划目录

```text
01-simulator/
├── README.md
├── app/
│   ├── main.py            FastAPI 入口
│   ├── world.py           世界状态与时钟
│   ├── swimmers.py        游客行为模型
│   ├── wristband.py       手环生理模型
│   ├── water.py           水质模型
│   └── scenarios.py       剧本加载与执行
├── scenarios/             5 条剧本 JSON（时间线）
├── seed/                  种子数据（泳池、区域、摄像头）
├── tests/                 pytest
└── requirements.txt
```

## 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 存活与当前规模 |
| GET | `/sim/snapshot?poolId=` | 当前世界快照（目标、姿态、手环、水质） |
| GET | `/sim/status` | 种子、剧本、时钟 |
| GET | `/sim/scenarios` | 剧本列表 |
| POST | `/sim/scenario/{key}` | 注入剧本（`drown_still` / `zone_intrude` / `night_intrude` / `water_poor`） |
| POST | `/sim/scenario/normal` | 恢复正常 |
| POST | `/sim/clock` | 调整演示时钟倍速 |
| POST | `/sim/seed?seed=&swimmerCount=` | 重新播种 |

## 运行

由 `deploy/compose.yaml` 托管，正常不单独启动：

```powershell
cd deploy\scripts
.\up.ps1 -NoBuild            # 只重启容器
.\logs.ps1 -Service simulator
```

容器内手动验证：

```powershell
docker --context home-dev exec smartpool-simulator python -c "import urllib.request,json;print(json.load(urllib.request.urlopen('http://127.0.0.1:8010/sim/snapshot?poolId=1'))['counts'])"
```

本地裸跑（调试用）：`pip install -r requirements.txt` 后 `uvicorn app.main:app --port 8010`。

## 设计约束

- 固定随机种子：同一 `seed` + 同一剧本 → 同一结果，保证演示可复现。
- 时钟由本服务统一提供，支持倍速；其它服务不自行推算时间。
- 输出坐标一律归一化 `0..1`。

## 相关文档

- [总体架构](../../notes/01-项目调研规划与开发建设记录/01-第一版-演示平台/03-架构设计/01-总体架构与数据流.md)
- [接口契约](../../notes/01-项目调研规划与开发建设记录/01-第一版-演示平台/03-架构设计/02-接口契约.md)
- [测试资产台账](../../notes/01-项目调研规划与开发建设记录/01-第一版-演示平台/06-测试数据与测试资产/01-测试资产台账.md)
