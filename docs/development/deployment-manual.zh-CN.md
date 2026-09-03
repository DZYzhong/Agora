# Agora 新服务器部署手册（运维用）

> 适用：把 Agora 生产栈部署到**一台新的服务器**（Linux 优先）。内容=组件与版本清单 → 基础环境准备 → 部署步骤 → 验证 → 运维要点。
> 代码基线：`codex/agora-p0`（schema `20260902_0019`）。中文版。

## 1. 组件与版本清单（必读）

| 组件 | 版本/规格 | 说明 |
|---|---|---|
| 操作系统 | Ubuntu 22.04/24.04 LTS x64（或等价 Linux；macOS 亦可但以下按 Linux） | 需要 root 或 sudo |
| Docker Engine | ≥ 24（本次验证环境 docker 29.5.2） | `docker --version` |
| Docker Compose | **v2 插件**（`docker compose version` ≥ 2.24）或独立 `docker-compose` ≥ 2.x | 二选一；本仓库 compose 文件兼容两者 |
| Git | ≥ 2.30 | 拉取 `codex/agora-p0` 分支 |
| OpenSSL | ≥ 3.0 | 生成自签 TLS 证书 |
| curl | 任意 | 冒烟 |
| 资源 | CPU ≥ 2 核、内存 ≥ 4 GiB（建议 6）、磁盘 ≥ 30 GiB 空闲 | 本机曾遇 40G 磁盘耗尽事故，务必预留 |
| 运行镜像（compose/build 拉取） | `postgres:16`、`redis:7`、`nginx:1.27-alpine`、`prom/prometheus:v2.54.1`、`node:22-slim`（web 构建）、`python:3.12-slim`（api/worker/migrate 构建） | 应用依赖在构建期由 `pyproject.toml`/`package-lock.json` 固定；**生产建议按本手册 §6 固定镜像 digest** |
| 端口（默认） | api 8000 · web 3000 · postgres 5432 · redis 6379 · nginx 8080(→8443) · prometheus 9091 | 与宿主机已有服务冲突时改 compose 映射 |
| 域名/TLS | 按决策**使用 IP:端口 + 自签证书**（§4.1），或替换为托管证书 | 证书 CN/SAN 指向服务器 IP |

## 2. 运维前置准备（基础环节，先做）

```bash
# 2.1 系统依赖
sudo apt-get update && sudo apt-get install -y curl git openssl ca-certificates

# 2.2 Docker Engine（官方源，示例 Ubuntu）
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"   # 重新登录生效

# 2.3 Compose v2 插件
sudo apt-get install -y docker-compose-plugin
docker compose version          # 期望 ≥ 2.24
# （或安装独立 docker-compose 亦可，脚本会自动探测两者）

# 2.4 资源自检
df -h /           # 空闲 ≥ 30GiB
free -h           # 可用内存 ≥ 4GiB
nproc             # ≥ 2

# 2.5 端口占用检查（冲突则改 infra/docker-compose.yml 的 ports）
sudo ss -ltnp | grep -E ':(8000|3000|5432|6379|8080|8443|9091)\b' || echo "端口空闲"

# 2.6 国内网络镜像（可选，拉镜像失败时配置 registry mirror）
# 编辑 /etc/docker/daemon.json:
# { "registry-mirrors": ["https://docker.1ms.run", "https://docker.m.daocloud.io"] }
sudo systemctl restart docker
```

## 3. 部署步骤

```bash
# 3.1 拉取代码（固定到已验收提交）
git clone git@github.com:DZYzhong/Agora.git agora
cd agora && git checkout codex/agora-p0
# 建议记录并固定 SHA（例）：git checkout <deployment-sha>

# 3.2 生成 secrets（gitignored infra/.env，随机值）
scripts/deploy_local.sh            # 自动生成 infra/.env + 自签证书 + up -d --build + 等待 /ready
# 或手工：cp 参考 infra/env.production.example，填 infra/.env

# 3.3 证书（IP 场景）——deploy_local.sh 默认 CN=localhost；改 IP 时：
mkdir -p .agora/certs
openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
  -keyout .agora/certs/agora.key -out .agora/certs/agora.crt \
  -subj "/CN=<服务器IP>" -addext "subjectAltName=IP:<服务器IP>"
docker-compose -f infra/docker-compose.yml restart nginx

# 3.4 引导 Admin（一次性）
scripts/deploy_local.sh --bootstrap-admin <admin用户名> '<强密码>'

# 3.5 冒烟（就绪+登录页+安全头）
scripts/deploy_local.sh --smoke
```

## 4. 验证清单

- `https://<IP>:8443/ready` → 200（configuration/database/schema 全 ok）
- Web `http://<IP>:3000/login` → 200；admin 登录 → 建项目/用户/成员/凭据页可用
- 安全头：`curl -kI https://<IP>:8443/health` 含 `x-content-type-options: nosniff` 等
- 指标：`http://<IP>:9091/targets` → `agora-api` health=up；`/metrics` 输出 `agora_ready 1`
- 备份：`AGORA_BACKUP_PASSPHRASE=... scripts/backup_db.sh` 产出加密文件
- 版本核对：`SELECT version_num FROM alembic_version` 应等于 `20260902_0019`

## 5. 运维要点

- **升级**：`git pull` → 先 `docker compose build api web worker migrate` → `up -d --no-deps migrate` → `up -d api worker web nginx`（migrate 先于应用）
- **备份**：每日 `scripts/backup_db.sh` + 加密文件**复制离主机**（DR 要求）；轮换保留 7 份
- **磁盘**：定期 `docker builder prune -af` 与 `docker image prune -f`；监控 `/var/lib/docker` 容量
- **监控**：Prometheus `http://<IP>:9091`；告警规则已加载 4 条；Alertmanager 接收人按环境配置
- **日志**：`docker compose logs -f api worker web`
- 详细运维见 `docs/development/local-production-runbook.zh-CN.md`

## 6. 生产加固建议（放行前由运维执行）

1. **固定镜像 digest**：`docker images --digests` 记录 postgres/redis/nginx/prometheus 及各业务镜像 digest 到部署记录。
2. 托管 TLS 证书替换自签（若提供 IP 证书/内网 CA 亦可）。
3. 为 compose 数据卷（postgres/prometheus）启用加密卷或主机级加密。
4. 设置备份 cron + 离主机目标 + 恢复演练排期（RPO≤24h/RTO≤4h）。
