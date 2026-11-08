# home-dev 远程开发环境（容器托管）

> 目标形态：**本机只留代码与文档，容器与数据库跑在家用电脑 home-dev**；需要看效果时在远端拉起，前端经 SSH 隧道在本地浏览器打开。
> 状态：**环境已全部打通**——引擎可启动、代理可拉镜像、隧道可访问页面（2026-11-05 实测）。

## 一、机器实测

| 项 | 实测值 | 说明 |
| --- | --- | --- |
| 主机名 | `DESKTOP-LHHD9GR` | SSH 别名 `home-dev`，免密可达 |
| 系统盘 | C:，总 111.5 GiB，**剩余 42.9 GiB**（拉完基础镜像后） | 单盘，无其它数据盘 |
| Docker 数据盘 | `docker_data.vhdx` 随镜像增长 | 现有 PowerSystem + 本项目基础镜像 |
| 内存 | 16 GiB，Docker VM 上限 7.7 GiB | 容器内存按 7.7 GiB 规划 |
| CPU | Intel i7-4790，4 核 8 线程 | 无独立 GPU，纯 CPU |
| 常驻服务 | PowerSystem 5 个中间件容器，约 870 MiB | 演示本项目时建议先停 |
| 代理 | Clash Verge，混合端口 `7897` | 已修复，可访问 GitHub / Docker Hub |
| 内网穿透 | `frpc.exe` 以服务方式常驻 | 可复用做公网展示 |

## 二、容量结论

| 资源 | 本项目占用量级 | 结论 |
| --- | --- | --- |
| 磁盘 | 基础镜像 2.6 GB + 业务镜像与数据 2–4 GB | 42.9 GB 够用，余量约 37 GB |
| 内存 | MySQL 0.8 + Redis 0.1 + 后端 JVM 0.8 + 推理 0.4 + Nginx 0.1 ≈ **2.2 GB** | 在 7.7 GiB 上限内；与 PowerSystem 并行时余量约 4.6 GB |
| CPU | 4 核 8 线程，无 GPU | 占位模型足够；真实 Mamba-YOLO 训练不要放这台 |

> 余量按「本仓库不存模型权重」计算。真实权重与 CUDA 镜像需另加 5–10 GB。

## 三、引擎启动（已验证）

远端无交互登录时，从 SSH 直接启动 `Docker Desktop.exe` 会立即退出（用户级安装、无 `com.docker.service`）。已建计划任务，在**已登录的桌面会话**中拉起：

```powershell
ssh home-dev schtasks /run /tn SmartPoolStartDocker
Start-Sleep 60
docker --context home-dev ps
```

- 前提：该机器保持一个活跃登录会话（向日葵或远程桌面）。
- 任务指向 `C:\Users\admin\AppData\Local\Programs\DockerDesktop\DOCKER~2.EXE`（8.3 短名，规避路径空格）。
- 引擎起来后 `unless-stopped` 的容器自动恢复。
- `AutoStart` 为 `false`，机器重启后仍需一次登录 + 运行该任务。

## 四、镜像加速（已打通）

远端与本地**都无法直连 Docker Hub**，必须让 Docker 引擎走 Clash 代理。踩过的坑与结论：

| 尝试 | 结果 |
| --- | --- |
| 直连 `registry-1.docker.io` | 超时 |
| `docker.m.daocloud.io` / `docker.1ms.run` | 清单可达，**blob 在境外 CDN，EOF** |
| `nju` / `sjtu` / `iscas` / `1panel.live` / `hpcloud` | 403 / TLS 失败 / EOF |
| `host.docker.internal:7897` 作代理 | 引擎侧 DNS 不解析该名 |
| **`192.168.111.234:7897` 作代理** | **可用**（容器网络与 daemon 均可达） |

**唯一正确的写法**（写进 `%APPDATA%\Docker\settings-store.json`，**键名必须小写**，写 PascalCase 不会生效）：

```json
{
  "AutoStart": false,
  "DisplayedOnboarding": true,
  "LastContainerdSnapshotterEnable": 1793147860,
  "LicenseTermsVersion": 2,
  "SettingsVersion": 48,
  "proxyHttpMode": "manual",
  "overrideProxyHttp": "http://192.168.111.234:7897",
  "overrideProxyHttps": "http://192.168.111.234:7897",
  "overrideProxyExclude": "localhost,127.0.0.1"
}
```

生效步骤：终止 `DOCKER~2.EXE` 与 `com.docker.backend.exe` → `schtasks /end` → 覆盖配置 → `schtasks /run` → 等 60 秒。

> 两个硬约束：① `proxyHttpMode` 不能写 `"none"`，会导致引擎起不来；② 代理地址依赖主机局域网 IP，IP 变化后需要同步修改。

## 五、已预置镜像

| 镜像 | 大小 | 用途 |
| --- | --- | --- |
| `mysql:8.0` | 1.1 GB | 业务库 |
| `redis:7.4.5-alpine` | 61 MB | 缓存与实时状态（复用现有） |
| `nginx:1.27-alpine` | 74.5 MB | 统一入口与静态资源 |
| `eclipse-temurin:17-jre-alpine` | 257 MB | 后端运行 |
| `maven:3.9-eclipse-temurin-17` | 775 MB | 后端构建（多阶段） |
| `python:3.11-slim` | 189 MB | 推理服务与模拟数据源 |
| `node:20-alpine` | 194 MB | 前端构建（多阶段） |

> 后端与前端一律多阶段构建，运行镜像只带 JRE / Nginx 静态文件，不带 Maven 与 Node。

## 六、远程访问（已验证）

实测把远端容器端口映射到本地并返回 HTTP 200：

```powershell
ssh -N -L 127.0.0.1:18080:127.0.0.1:18080 home-dev
# 远端：docker --context home-dev run -d -p 127.0.0.1:18080:80 nginx:1.27-alpine
# 本地浏览器 http://127.0.0.1:18080 → HTTP 200
```

本项目固定用法：远端 Nginx 发布到 `127.0.0.1:18080`，本地隧道同名端口，浏览器访问 `http://127.0.0.1:18080`。`/api`、`/ws` 与页面同源，无需额外 CORS 配置。

## 七、落地步骤

1. 远端建目录 `C:\home-dev\smartpool`，同步同一仓库源码。
2. `docker --context home-dev compose -f deploy/compose.yaml up -d --build --wait`。
3. 健康检查：`ssh home-dev "curl.exe --fail --silent http://127.0.0.1:18080/api/health"`。
4. 本地起隧道后打开页面，按剧本走一遍告警闭环。
5. 把批次写进 `notes/04-部署发布与变更记录/部署与运维日志/`。

## 八、不要做的事

- 不要在本地起 MySQL/Redis 再从远端连，双份数据源会导致演示不一致。
- 不要 `docker compose down -v`（会连 PowerSystem 的卷一起删）。
- 不要把模型权重、数据集放系统盘根目录；统一放 `C:\home-dev\smartpool\artifacts\`。
- 不要把 3306/6379/8000 暴露公网；对外只开 80/443。
- 不要改 Windows 自动登录或 Docker 服务安装方式来「省掉登录」。

## 九、本次改动记录（2026-11-05）

| 改动 | 位置 | 是否保留 |
| --- | --- | --- |
| 计划任务 `SmartPoolStartDocker` | 远端任务计划程序 | 保留（每次启动引擎用） |
| 代理配置（小写键名） | `%APPDATA%\Docker\settings-store.json` | 保留（拉镜像必需） |
| 原始配置备份 | `C:\home-dev\settings-store.bak-20261105.json` | 保留（回滚用） |
| 临时 base64 / 中间文件 | `C:\home-dev\*` | 已删除 |
| 验证用容器与镜像 | `smartpool-smoke`、`hello-world` | 已删除 |

## 相关文档

- [部署与服务器上传规范](../../notes/02-工程规范边界与验收治理/项目工程规范/06-部署与服务器上传规范.md)
- [部署与运维日志索引](../../notes/04-部署发布与变更记录/部署与运维日志/00-索引·部署与运维日志.md)
- [当前系统状态](../../notes/00-当前系统状态.md)
