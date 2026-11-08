# deploy · 编排与演示环境

> 一套 Compose 起全部服务，Nginx 做统一入口。**本目录是部署命令的唯一维护处。**
> 状态：**M1 已落地并在 home-dev 跑通**（6 个容器全部 healthy）。

## 一、实际结构

```text
deploy/
├── compose.yaml            mysql / redis / simulator / ai / backend / nginx
├── .env.example            环境变量模板（真实值只在远端 deploy/.env）
├── home-dev/README.md      远端机器实测、引擎启动与镜像加速说明
└── scripts/
    ├── sync.ps1            打包源码 -> scp -> 远端解包
    ├── up.ps1              同步 + 首次生成随机凭据 + 构建 + 启动
    ├── down.ps1            停止容器（保留数据卷）
    ├── logs.ps1            查看指定服务日志
    ├── tunnel.ps1          建立本地 18080 隧道
    ├── reset.ps1           重新播种模拟世界并清空风险窗口
    ├── smoke.py            M1 冒烟：健康、登录、快照、鉴权
    └── check_ws.py         WebSocket 握手与推送验证
```

> 脚本内的控制台输出一律用 ASCII：Windows PowerShell 5.1 会按 ANSI 读取脚本文件，中文会变成乱码。写新脚本时遵守这一条。

## 二、端口与暴露

| 服务 | 容器端口 | 宿主机发布 | 对外 |
| --- | --- | --- | --- |
| nginx | 80 | `127.0.0.1:18080` | 经 SSH 隧道 |
| backend | 8080 | 未发布 | 否 |
| ai | 8000 | 未发布 | 否 |
| simulator | 8010 | 未发布 | 否 |
| mysql | 3306 | 未发布 | 否 |
| redis | 6379 | 未发布 | 否 |

> 只有 Nginx 发布到宿主机回环地址，其余服务都在 compose 网络内；远程访问靠 SSH 隧道，符合 [部署与服务器上传规范](../notes/02-工程规范边界与验收治理/项目工程规范/06-部署与服务器上传规范.md)。

## 三、日常命令

```powershell
cd deploy\scripts

.\up.ps1                 # 同步 + 构建 + 启动（首次会生成随机口令）
.\up.ps1 -SkipSync       # 只重建镜像并重启
.\up.ps1 -NoBuild        # 只重启容器
.\tunnel.ps1             # 另开窗口保持，浏览器打开 http://127.0.0.1:18080
.\logs.ps1 -Service ai   # 看推理服务日志
.\reset.ps1              # 重置演示世界
.\down.ps1               # 停止（不删卷）
```

验收：

```powershell
python deploy\scripts\smoke.py      # 需要隧道在跑
python deploy\scripts\check_ws.py
```

## 四、镜像构建

| 服务 | 基础镜像 | 构建要点 |
| --- | --- | --- |
| backend | maven:3.9-eclipse-temurin-17 → eclipse-temurin:17-jre-alpine | 多阶段；`settings.xml` 走阿里云 Maven 镜像 |
| nginx | node:20-alpine → nginx:1.27-alpine | 多阶段；`registry.npmmirror.com` |
| ai / simulator | python:3.11-slim | `PIP_INDEX_URL` 走阿里云 PyPI |

> 运行镜像不含 Maven、Node 与源码；容器内以非 root 用户运行。

## 五、数据与卷

| 卷 | 用途 |
| --- | --- |
| `smartpool-mysql-data` | 业务库（Flyway 自动建表 + 种子） |
| `smartpool-redis-data` | 实时快照缓存（AOF） |

- 禁止 `docker compose down -v`：会连 PowerSystem 的卷一起删。
- 重建数据：`docker volume rm smartpool-mysql-data` 后重新 `up`，Flyway 会重放 V1/V2。

## 六、首次启动注意

1. 远端需保持桌面登录会话，并先执行 `ssh home-dev schtasks /run /tn SmartPoolStartDocker` 拉起 Docker 引擎。
2. `deploy/.env` 只在远端生成，不入 Git；`up.ps1` 首次运行会自动创建。
3. JWT 密钥长度不足 32 字节时后端会补零，但仍应在 `.env` 中使用 48 位随机串。

## 相关规范

- [home-dev 远程开发环境](home-dev/README.md)
- [部署与服务器上传规范](../notes/02-工程规范边界与验收治理/项目工程规范/06-部署与服务器上传规范.md)
- [部署与运维日志索引](../notes/04-部署发布与变更记录/部署与运维日志/00-索引·部署与运维日志.md)
