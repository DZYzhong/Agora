# C1 干净主机部署操作记录（2026-09-03）

> 目标：黑盒检查单 C1——按部署手册 `docs/development/deployment-manual.zh-CN.md` 在全新主机部署，`verify_production.sh` PASS。
> 主机：**172.29.30.128**（用户 jishu，sudo 密码与 ssh 同源；操作凭据未写入本文档——admin 密码在 `/tmp/c1_admin_pass.txt`，备份口令在 `/tmp/c1_bkpass.txt`，均为本机临时文件）。
> 基线：`codex/agora-p0` @ `a1b6de7`（schema `20260902_0019`）。

## 1. 主机事实（探测记录）

- OS：CentOS Linux 7 (Core)，内核 3.10.0-957.el7.x86_64（EOL；手册首选 Ubuntu，本机按"等价 Linux"处理，见 §5 差异）
- CPU 8 核；内存 62G（可用 44G）；`/` 空闲 71G（xfs）
- 预装：docker-ce 19.03.9（engine）+ cli 20.10.9、docker-compose v1 1.27.4、git、openssl 1.0.2k、curl
- python3 **不存在**（CentOS7 仅 python2）；sudo 需要密码
- 端口 8000/3000/5432/6379/8080/8443/9091 初始空闲
- 已有第三方容器：dataease（8110）、mysql-de（内部）——非本次部署，保持不动

## 2. 网络约束与适配（重要差异）

- 外网受限：**docker.io / github.com 不可达**（000）；可达：aliyun、docker.m.daocloud.io、docker.1ms.run、pypi.org、pypi.tuna、registry.npmjs.org、deb.debian.org
- 适配动作：
  1. docker daemon.json 配置 registry 镜像源 `docker.m.daocloud.io`（首选）+ `docker.1ms.run`，重启 docker → `docker pull alpine/postgres:16/redis:7/nginx:1.27-alpine/prometheus/node/python` 全部成功（镜像层走镜像源）
  2. compose v2：github 被墙无法下载二进制；改从本机经 gh-proxy 镜像下载官方 `docker-compose-linux-x86_64` v2.29.7（61MB，ELF 静态），scp 到主机替换 v1（备份为 `docker-compose-v1.bak`）→ `Docker Compose version v2.29.7`；`deploy_local.sh`/`verify_production.sh` 自动回退逻辑命中 standalone `docker-compose`
  3. pip（pypi.org 可达）、npm（registry.npmjs.org 可达）、apt（deb.debian.org 可达）均直连，无需改源
  4. 代码传输：github 不可达 → 从本机打包主仓库（含 .git，排除 .venv/node_modules/.next/.worktrees 等）7.7MB → scp → 解压 `~/agora` → `git checkout codex/agora-p0` → **HEAD=a1b6de72**（与本地/远端一致）

## 3. 逐步操作时间线（全部命令均有执行输出，汇总如下）

| 步骤 | 操作 | 结果 |
|---|---|---|
| 1 | SSH 连通 + 主机事实（§1） | OK |
| 2 | 启动 docker daemon；`usermod -aG docker jishu`（新会话生效）；`systemctl enable docker` | 19.03.9 / overlay2 / cgroupfs |
| 3 | 配 registry 镜像源并重启；预拉 7 个基础镜像（alpine 冒烟通过） | OK |
| 4 | 安装 compose v2.29.7（standalone，备份 v1） | `docker-compose version` = v2.29.7 |
| 5 | 生成 TLS 证书：主机 openssl 1.0.2 不支持 `-addext` → 改用 extfile 配置；`CN=172.29.30.128`，SAN=`IP:172.29.30.128,DNS:localhost,IP:127.0.0.1`，365 天 | 生成 `.agora/certs/agora.{crt,key}` |
| 6 | `deploy_local.sh`：生成 infra/.env（3 个随机 token）→ compose build+up | 首次因端口冲突中断，见 §4 |
| 7 | 端口冲突适配后再次 `docker-compose up -d` | api/web/nginx/worker/prometheus/postgres/redis 全 up |
| 8 | `deploy_local.sh --bootstrap-admin admin <强随机密码>` | `Admin admin bootstrapped for org local-org` |
| 9 | `deploy_local.sh --smoke` | **SMOKE PASS**（/ready 200、/login 200、3 项安全头） |
| 10 | `verify_production.sh`（两次：过程性 + 终态） | **PRODUCTION ACCEPTANCE PASS（7/7）** |
| 11 | 主机侧加密备份 `scripts/backup_db.sh` | `agora-20260903T131301Z.enc`（94,528B） |
| 12 | 备份复制离主机（DR 要求）：scp 到本机 `.agora/c1-backups/` | 94,528B 已落地 |
| 13 | 本机（外部视角）验证：`https://172.29.30.128:8443/ready`；证书 SAN（IP:172.29.30.128…）；admin API 登录 | ready 200 / SAN 正确 / login 200 |

## 4. 问题与处置（记录）

1. **docker daemon 未启动**（CentOS7 service）→ `systemctl start/enable docker`。
2. **sudo 密码传递**：expect 驱动 ssh；远端脚本用占位符烘焙真实密码（`__PW__`→替换），日志不落密码。
3. **dockerhub/github 不可达** → 镜像源 + 本机打包代码 + gh-proxy 下载 compose（§2）。
4. **openssl 1.0.2 无 `-addext`**（手册要求 ≥3.0）→ extfile 生成含 SAN 的证书（§3-5），记录到部署差异。
5. **api 宿主端口 8000 冲突**：compose bind 0.0.0.0:8000 报 "address already in use"，但 ss/netstat/lsof 均无 LISTEN；实测 127.0.0.1:8000 被某隐藏进程占用（0.0.0.0:8001/3000/8080/8443/9091 均空闲）。按手册"端口冲突改 compose 映射"，仅改主机这份部署副本：`api ports: "8001:8000"`（nginx 内网仍走 api:8000，不受影响）。后续 `verify_production.sh` 不依赖宿主 8000。
6. **compose v2 优先级**：`deploy_local.sh` 优先 `docker compose`（CLI 插件）→ 主机无插件 → 命中 standalone `docker-compose` v2.29.7。

## 5. 版本/镜像清单（对应手册 §6 加固记录）

- 应用代码：`codex/agora-p0` @ `a1b6de7`；schema `20260902_0019`
- docker engine 19.03.9；compose **v2.29.7**（standalone）；openssl 1.0.2k（CentOS7 系统自带，证书经 extfile 生成）
- 运行容器：infra-api(healthy, 8001→8000) / infra-web(3000) / infra-nginx(8080,8443 TLS) / infra-postgres(5432,healthy) / infra-redis(6379) / infra-worker / infra-prometheus(9091)
- 拉取镜像 digest（手册 §6.1）：
  - postgres:16 `sha256:f1c3376c26f2609ab9f29f71f824103fe2fcd8ee0346485cb6122a4f93df6f94`
  - redis:7 `sha256:71da9275c5f3fcb97d0fa0c8c5b36cc995327265420f17a04bfd544f458059f7`
  - nginx:1.27-alpine `sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10`
  - prom/prometheus:v2.54.1 `sha256:f6639335d34a77d9d9db382b92eeb7fc00934be8eae81dbc03b31cfe90411a94`
  - python:3.12-slim `sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea`
  - node:22-slim `sha256:83f487e0a63425e5b4d146fb5e5be574bcbe1b7b843d3ebafdd95eaf7767a7e5`
  - 本地构建镜像（infra-api/web/worker/migrate/local-connector）由源码 SHA a1b6de7 固定（本地构建无 registry digest；如需锁 digest 需推送 registry）

## 6. 验收结果

- `scripts/deploy_local.sh --smoke` → **SMOKE PASS**
- `scripts/verify_production.sh` → **PRODUCTION ACCEPTANCE PASS**（api /ready、安全头、metrics agora_ready=1、web /login 200、schema 20260902_0019、prometheus target up、outbox retryable 0——7/7）
- 外部视角（本机→主机）：`https://172.29.30.128:8443/ready` = ready；证书含 `IP:172.29.30.128` SAN；admin 登录成功
- 备份：主机生成加密备份并**已复制离主机**（本机 `.agora/c1-backups/agora-20260903T131301Z.enc`）

## 7. 遗留说明（非阻塞）

- CentOS7 为 EOL 系统：生产建议迁移到手册首选 Ubuntu 24.04；本机 openssl 1.0.2 与内核 3.10 均偏旧，功能验证不受影响
- 部署副本的 compose 已按 §4-5 记录改映射（8001）；仓库内 compose 保持原样；正式升级流程请把该映射沉淀为仓库可配置项或部署 override
- 该主机存在第三方服务（dataease/mysql），非 Agora 栈，端口互不冲突
