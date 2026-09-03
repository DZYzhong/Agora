# C1 执行计划：移除服务端本地初始化残留（2026-09-03）

> 上游：`docs/superpowers/plans/2026-09-02-production-ready-web-deploy.md` C1（原保守挂起，2026-09-03 用户确认执行）。
> 原则：**生产面删干净，dev/test seeding 能力保留但不经 HTTP**；遵循流程（pytest 绿、Change-Id、docs: record）。

## 1. 目标与边界

- 目标：Agora 代码库中不再存在"服务端扫描本地仓库"的对外 API 与 Web 关联路径；该能力只作为**测试/本地脚本的 seeding 工具**（直接调用服务层），且显式标注。
- 非目标：删除资产/索引/知识域本身；不破坏 e2e（p0/p2 loop）、黑盒脚本、demo 文档的本地使用方式（它们改为调用 service 层 helper）。

## 2. 现状（实测清单）

- API：`POST /projects/{id}/initialize-local`、`POST .../initialization-jobs/{job_id}/retry`、`GET .../initialization-jobs`（`apps/api/routers/projects.py`，生产已 404 via `_hide_local_initialization_in_production`）。
- 中间件 `HideProductionLocalInitializationMiddleware`（`apps/api/middleware.py`）+ `main.py` custom_openapi 生产裁剪这两处**仅在存在路由时需要**。
- harness：`repo_path` 在协议 1.1 下已被拒绝（`LOCAL_REPO_PATH_REJECTED`），生产同样拒绝；legacy 分支校验路径（保留运行时策略拒绝，作为 C1 的"运行时策略拒绝"保留面）。
- worker：`apps/workers/workflows/initialize_project.py`（`initialize_project_from_local_repo`）→ `apps/workers/activities/git_sync.analyze_local_repo` 等本地扫描实现。
- 模型/表：`ProjectInitializationJobModel`（`packages/core/models.py`，0003 迁移建表）+ `packages/core/repositories/initialization_jobs.py`。
- Web：项目首页初始化状态面板 + 历史（`apps/web/app/projects/[projectId]/page.tsx`）；`apps/web/app/page.tsx` 引用。
- 脚本：`scripts/prepare_p2_blackbox.py`、`scripts/run_p0_demo.py`（本地 seeding）。
- 测试（15 个文件引用，多为 seeding 用途）：e2e loops、harness/context/sessions/work_items/usable API、`test_initialization_jobs.py`、`test_p0_loop`、worker 初始化测试、`test_web_config.py`、`test_p2_migration.py` 等。

## 3. 设计决策

1. **API/中间件/openapi 裁剪全部删除**（生产与 dev 都不再暴露 HTTP 初始化面）。
2. **seeding 收敛为 service 层函数**：把 `initialize_project_from_local_repo` + job 记录下沉为一个显式的 `packages/core/services/local_seed.py::seed_project_from_local_repo(...)`（内部仍走 worker activities；**仅测试/脚本 import**，模块头标注 "dev/test seeding only, not part of the product API"）。
3. `ProjectInitializationJobModel` 表：**保留表结构数据但不再被产品代码引用**——先改为仅由 local_seed 记录；是否删表放入 PR4 之后（避免本批为删表新增迁移+破坏既有数据）。C1.1 的"删干净"针对 API/Web 路径；表保留并在计划中说明（诚实记录）。
4. Web：项目首页移除初始化面板与历史（随 UI 重设计 B3 一并做视觉收尾，功能先删）。
5. 脚本：`prepare_p2_blackbox.py`、`run_p0_demo.py` 顶部标注"仅本地开发/测试用"。
6. 测试迁移：使用 `initialize-local` HTTP 的测试改为调用 `seed_project_from_local_repo` helper 或既有 fixture；`test_initialization_jobs.py` 改为针对 service 层 job 记录行为。

## 4. 批次与验收

| 批次 | 内容 | 验收 |
|---|---|---|
| C1-B1 | service 层 `local_seed` 收敛 + 删除 3 个 API 端点/中间件/openapi 裁剪 + main 注册清理 | 相关 API 测试改走 helper；pytest 相关文件绿 |
| C1-B2 | 迁移测试文件（15 个引用文件逐一改 helper/标注）| 全量 pytest 绿 |
| C1-B3 | web 首页移除初始化面板/历史 + scripts 标注 | tsc + build + test_web_config 绿 |
| C1-B4 | docs: record + roadmap 更新 + 计划勾选 | 提交链完整 |

## 5. 风险

- harness legacy 分支仍引用 `_validate_local_initialization_path`：保留该校验函数（生产=拒绝），仅删 HTTP 端点与中间件。
- e2e loops 依赖 seeding：helper 必须覆盖"建 job → 扫描 → 资产入库 → 状态回写"原行为，先写 helper 单测再迁移调用方。
