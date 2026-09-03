# Agora 运维指标与告警（本机证据版）

> 证据采样：2026-09-03 `https://127.0.0.1:8443/metrics`（Prometheus 文本）与 `scripts.agora_admin retention-summary`（live PG）。

## 1. 指标（Prometheus 文本，`GET /metrics`）

实测输出（节选）：

```
# TYPE agora_ready gauge
agora_ready 1
# TYPE agora_schema_revision_info gauge
agora_schema_revision_info{status="SCHEMA_CURRENT"} 1
# TYPE agora_projects_total gauge
agora_projects_total 1
# TYPE agora_pending_context_proposals_total gauge
agora_pending_context_proposals_total 0
# TYPE agora_outbox_retryable_total gauge
agora_outbox_retryable_total 0
```

- `agora_ready`：1=ready；0=配置/数据库/schema 任一失败（与 `/ready` 一致）。
- `agora_schema_revision_info`：label 为 SCHEMA_CURRENT / SCHEMA_REVISION_STALE 等。
- `agora_projects_total` / `agora_pending_context_proposals_total`：治理负载。
- `agora_outbox_*`：事件积压/可重试计数（worker 健康）。

采集建议：Prometheus `scrape_configs` 指向 `https://<host>:8443/metrics`（自签需 `tls_config.insecure_skip_verify` 或换托管证书），`scrape_interval: 15s`。

## 2. 建议告警规则（Alertmanager/grafana，本仓库以配置文档交付）

```yaml
groups:
  - name: agora
    rules:
      - alert: AgoraNotReady
        expr: agora_ready == 0
        for: 2m
        labels: { severity: critical }
        annotations:
          summary: "Agora /ready 失败（数据库/schema/配置）"
      - alert: AgoraSchemaStale
        expr: agora_schema_revision_info{status!="SCHEMA_CURRENT"} == 1
        labels: { severity: critical }
        annotations: { summary: "schema 与迁移 head 不一致，先跑 migrate" }
      - alert: AgoraOutboxBacklog
        expr: agora_outbox_retryable_total > 0
        for: 10m
        labels: { severity: warning }
        annotations: { summary: "outbox 出现可重试积压，检查 worker" }
```

## 3. 保留/清理（retention）

```bash
# 只读盘点
docker-compose -f infra/docker-compose.yml exec api python -m scripts.agora_admin \
  retention-summary --database-url postgresql+psycopg://agora:agora@postgres:5432/agora
# 清理终态（导出+删除候选；本机实测候选 0）
docker-compose -f infra/docker-compose.yml exec api python -m scripts.agora_admin \
  cleanup-retention --database-url postgresql+psycopg://agora:agora@postgres:5432/agora --yes
```

本机证据：`retention-summary` 返回 `{"exports": {"candidates": 0, ...}, "outbox": {"candidate_total": 0, ...}}`（2026-09-03T06:57Z）。

## 4. 未达项（诚实）

- Alertmanager/Grafana 实际接线、PR5-PERF（50 并发 30 分钟 p95）需生产环境/基准后做。

## 5. 性能冒烟基线（2026-09-03，`scripts/perf_smoke.py`）

- 目标：`https://127.0.0.1:8443/ready`，8 并发 × 32 请求（nginx 限流 20r/s+burst40 内）
- 结果：ok=32/32，errors=0；p50=217ms，p95=458ms，p99=491ms（含 TLS 握手与 /ready DB 探测）
- 说明：nginx `location /` 对 API 施加 20r/s+burst40 限流（设计行为）；正式 PR5-PERF（50 并发 30 分钟、§8.1 p95）需固定基准且绕过限流或调高阈值。

## 6. Prometheus 实例（2026-09-03 上线证据）

- compose 新增 `prometheus`（`infra/monitoring/prometheus.yml`，抓 `http://api:8000/metrics`；规则 `agora-alerts.yml` 已加载 4 条）；宿主端口 **9091**（9090 被本机 Stash 占用，见端口冲突说明）。
- 验证：`/-/ready` 200；target `agora-api` health=up（无 lastError）；`/api/v1/rules` 1 group / 4 rules。
- Alertmanager：接收器按运维配置（示例 `alertmanager.yml` 含占位 webhook），未随 compose 常驻。
