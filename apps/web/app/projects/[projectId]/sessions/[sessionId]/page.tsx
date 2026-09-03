import Link from "next/link";
import { apiGet } from "../../../../../lib/api";
import { currentLang } from "../../../../../lib/i18n";
import { relativeTime } from "../../../../../lib/format";
import { Badge, Card, Page, PageHeader, SectionLabel } from "../../../../../components/ui";

type SessionAudit = {
  id: string;
  project_id: string;
  task_id: string | null;
  work_item: {
    id: string;
    external_key: string | null;
    title: string;
    status: string;
    stage: string;
    source: string;
  } | null;
  agent_type: string;
  intent: string;
  status: string;
  created_at: string;
  closed_at: string | null;
  audit_counts: {
    events: number;
    context_packs: number;
    skill_runs: number;
    writebacks: number;
    development_updates: number;
  };
  development_updates: Array<{
    writeback_id: string;
    writeback_type: string | null;
    writeback_status: string | null;
    accepted_asset_id: string | null;
    summary: string;
    changed_files: Array<{ path: string; status: string; category: string }>;
    tests: Array<{ command: string; status: string; raw: string }>;
    risks: string[];
    follow_ups: string[];
    created_at: string;
  }>;
  context_packs: Array<{
    id: string;
    level: string;
    summary: string;
    key_facts: Array<{ fact: string; source_refs: string[] }>;
    source_refs: Array<{
      asset_id: string;
      asset_type?: string;
      title: string;
      source_uri?: string;
      chunk_id: string;
      preview?: string;
    }>;
    created_at: string;
  }>;
  skill_runs: Array<{
    id: string;
    skill_id: string;
    skill_name: string;
    input: Record<string, unknown>;
    output: Record<string, unknown>;
    warnings: string[];
    status: string;
    created_at: string;
  }>;
  writebacks: Array<{
    id: string;
    type: string;
    title: string;
    content: string;
    asset_refs: string[];
    status: string;
    accepted_asset_id: string | null;
    created_at: string;
  }>;
  events: Array<{ id: string; event_type: string; payload: Record<string, unknown>; created_at: string }>;
};

const dt = "text-xs text-ink-3";
const dd = "text-ink";

function StatusPill({ children, tone }: { children: string; tone?: "green" | "red" | "amber" | "slate" | "blue" }) {
  return <Badge tone={tone ?? "slate"}>{children}</Badge>;
}

export default async function SessionAuditPage({
  params,
}: {
  params: Promise<{ projectId: string; sessionId: string }>;
}) {
  const { projectId, sessionId } = await params;
  const lang = await currentLang();
  const zh = lang === "zh";

  let audit: SessionAudit | null = null;
  try {
    audit = await apiGet<SessionAudit>(`/projects/${projectId}/sessions/${sessionId}`);
  } catch {
    audit = null;
  }

  if (!audit) {
    return (
      <Page>
        <PageHeader title={zh ? "会话审计" : "Session audit"} />
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {zh ? "会话不存在。" : "Session not found."}
        </div>
        <p className="mt-4">
          <Link href={`/projects/${projectId}/sessions`} className="text-sm font-medium text-blue-600 hover:text-blue-700">
            ← {zh ? "返回会话列表" : "Back to sessions"}
          </Link>
        </p>
      </Page>
    );
  }

  return (
    <Page>
      <PageHeader
        title={audit.intent}
        subtitle={`${audit.agent_type} · ${audit.id}`}
        meta={<StatusPill tone={audit.status === "closed" ? "slate" : audit.status === "failed" ? "red" : "green"}>{audit.status}</StatusPill>}
        actions={
          <div className="flex items-center gap-2">
            {audit.work_item ? (
              <Link
                href={`/projects/${projectId}/work-items/${audit.work_item.id}`}
                className="rounded-lg border border-slate-300 bg-surface px-3 py-1.5 text-sm font-medium text-ink shadow-sm hover:bg-canvas"
              >
                {zh ? "查看工作项" : "View work item"}
              </Link>
            ) : null}
            <Link
              href={`/projects/${projectId}/sessions`}
              className="rounded-lg border border-slate-300 bg-surface px-3 py-1.5 text-sm font-medium text-ink shadow-sm hover:bg-canvas"
            >
              ← {zh ? "会话列表" : "Sessions"}
            </Link>
          </div>
        }
      />

      <Card className="mt-6 p-5">
        <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm sm:grid-cols-3 lg:grid-cols-5">
          <div>
            <dt className={dt}>{zh ? "工作项" : "Work item"}</dt>
            <dd className="truncate">{audit.work_item ? audit.work_item.title : audit.task_id ?? (zh ? "未设置" : "Not set")}</dd>
          </div>
          <div>
            <dt className={dt}>{zh ? "任务键" : "Task key"}</dt>
            <dd className="truncate font-mono text-xs">{audit.work_item?.external_key ?? audit.task_id ?? "—"}</dd>
          </div>
          <div>
            <dt className={dt}>{zh ? "开始" : "Started"}</dt>
            <dd>{relativeTime(audit.created_at, lang)}</dd>
          </div>
          <div>
            <dt className={dt}>{zh ? "关闭" : "Closed"}</dt>
            <dd>{audit.closed_at ? relativeTime(audit.closed_at, lang) : zh ? "进行中" : "Open"}</dd>
          </div>
          <div>
            <dt className={dt}>Dev updates</dt>
            <dd>{audit.audit_counts.development_updates}</dd>
          </div>
        </dl>
        <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 border-t border-edge-1 pt-3 text-sm sm:grid-cols-4">
          {(
            [
              ["Context", audit.audit_counts.context_packs],
              ["Skill runs", audit.audit_counts.skill_runs],
              ["Writebacks", audit.audit_counts.writebacks],
              ["Events", audit.audit_counts.events],
            ] as [string, number][]
          ).map(([label, value]) => (
            <div key={label} className="flex items-center justify-between">
              <dt className="text-ink-3">{label}</dt>
              <dd className="font-semibold text-ink">{value}</dd>
            </div>
          ))}
        </dl>
      </Card>

      <SectionLabel>{zh ? "开发更新" : "Development updates"}</SectionLabel>
      {audit.development_updates.length ? (
        <div className="mt-3 space-y-4">
          {audit.development_updates.map((update) => (
            <Card key={`${update.writeback_id}-${update.created_at}`} className="p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="text-[15px] font-semibold text-ink">{update.summary}</h3>
                  <p className="mt-0.5 font-mono text-xs text-ink-3">
                    {update.writeback_type ?? "development_update"} · {update.writeback_status ?? "unknown"}
                  </p>
                </div>
                <Badge tone={update.accepted_asset_id ? "green" : "amber"} dot={false}>
                  {update.accepted_asset_id ? "accepted" : "draft"}
                </Badge>
              </div>
              <div className="mt-3 grid gap-4 border-t border-edge-1 pt-3 sm:grid-cols-2">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-ink-3">
                    {zh ? "变更文件" : "Changed files"}
                  </p>
                  {update.changed_files.length ? (
                    <ul className="mt-2 space-y-1">
                      {update.changed_files.map((file) => (
                        <li key={`${update.writeback_id}-${file.path}`} className="flex items-center justify-between gap-2 text-sm">
                          <code className="truncate font-mono text-xs text-ink">{file.path}</code>
                          <span className="shrink-0 text-xs text-ink-3">
                            {file.category} · {file.status}
                          </span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-1 text-xs text-ink-3">—</p>
                  )}
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-ink-3">
                    {zh ? "测试" : "Tests"}
                  </p>
                  {update.tests.length ? (
                    <ul className="mt-2 space-y-1">
                      {update.tests.map((test) => (
                        <li key={`${update.writeback_id}-${test.raw}`} className="flex items-center justify-between gap-2 text-sm">
                          <code className="truncate font-mono text-xs text-ink">{test.command}</code>
                          <span className="shrink-0 text-xs text-ink-3">{test.status}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-1 text-xs text-ink-3">{zh ? "无测试记录" : "No tests recorded."}</p>
                  )}
                </div>
              </div>
              <div className="mt-3 grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-ink-3">
                    {zh ? "风险" : "Risks"}
                  </p>
                  <ul className="mt-1 list-disc space-y-0.5 pl-4 text-sm text-ink-2">
                    {update.risks.map((risk) => (
                      <li key={`${update.writeback_id}-${risk}`}>{risk}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-ink-3">
                    {zh ? "后续" : "Follow-ups"}
                  </p>
                  <ul className="mt-1 list-disc space-y-0.5 pl-4 text-sm text-ink-2">
                    {update.follow_ups.map((followUp) => (
                      <li key={`${update.writeback_id}-${followUp}`}>{followUp}</li>
                    ))}
                  </ul>
                </div>
              </div>
              {update.writeback_id ? (
                <p className="mt-3 border-t border-edge-1 pt-2 font-mono text-xs text-ink-3">
                  Writeback: {update.writeback_id}
                </p>
              ) : null}
            </Card>
          ))}
        </div>
      ) : (
        <Card className="mt-3 p-5 text-sm text-ink-3">
          {zh ? "无结构化开发更新。" : "No structured development updates recorded."}
        </Card>
      )}

      <SectionLabel>{zh ? "上下文包" : "Context packs"}</SectionLabel>
      {audit.context_packs.length ? (
        <div className="mt-3 space-y-4">
          {audit.context_packs.map((contextPack) => (
            <Card key={contextPack.id} className="p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-xs font-medium text-ink-3">ContextPack</p>
                  <h3 className="text-[15px] font-semibold text-ink">{contextPack.level}</h3>
                  <p className="mt-0.5 font-mono text-xs text-ink-3">{contextPack.id}</p>
                </div>
                <Badge tone="blue" dot={false}>
                  {contextPack.source_refs.length} {zh ? "来源" : "sources"}
                </Badge>
              </div>
              <pre className="mt-3 max-h-48 overflow-auto whitespace-pre-wrap rounded-lg bg-canvas p-3 text-sm text-ink-2">
                {contextPack.summary}
              </pre>
              {contextPack.source_refs.length ? (
                <div className="mt-3 space-y-2">
                  {contextPack.source_refs.map((source) => (
                    <div key={source.chunk_id} className="rounded-xl border border-edge-1 bg-fill/60 p-3">
                      <p className="text-sm font-semibold text-ink">{source.title}</p>
                      <p className="mt-0.5 font-mono text-xs text-ink-3">
                        {source.asset_type ?? "source"} · {source.source_uri ?? source.asset_id}
                      </p>
                      {source.preview ? <p className="mt-1 text-sm text-ink-2">{source.preview}</p> : null}
                    </div>
                  ))}
                </div>
              ) : null}
            </Card>
          ))}
        </div>
      ) : (
        <Card className="mt-3 p-5 text-sm text-ink-3">{zh ? "无上下文包。" : "No context packs recorded."}</Card>
      )}

      <SectionLabel>{zh ? "技能运行" : "Skill runs"}</SectionLabel>
      {audit.skill_runs.length ? (
        <div className="mt-3 space-y-2">
          {audit.skill_runs.map((run) => (
            <Card key={run.id} className="p-4">
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm font-semibold text-ink">{run.skill_name}</span>
                <Badge tone={run.status === "failed" ? "red" : run.status === "running" ? "blue" : "slate"}>
                  {run.status}
                </Badge>
              </div>
              <p className="mt-1 text-xs text-ink-3">{relativeTime(run.created_at, lang)}</p>
              <pre className="mt-2 max-h-48 overflow-auto rounded-lg bg-canvas p-3 text-xs text-ink-2">
                {JSON.stringify({ input: run.input, output: run.output, warnings: run.warnings }, null, 2)}
              </pre>
            </Card>
          ))}
        </div>
      ) : (
        <Card className="mt-3 p-5 text-sm text-ink-3">{zh ? "无技能运行。" : "No skill runs recorded."}</Card>
      )}

      <SectionLabel>{zh ? "写回" : "Writebacks"}</SectionLabel>
      {audit.writebacks.length ? (
        <div className="mt-3 space-y-2">
          {audit.writebacks.map((writeback) => (
            <Card key={writeback.id} className="p-4">
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm font-semibold text-ink">{writeback.title}</span>
                <Badge tone={writeback.status === "accepted" ? "green" : writeback.status === "rejected" ? "red" : "amber"} dot={false}>
                  {writeback.status}
                </Badge>
              </div>
              <p className="mt-0.5 font-mono text-xs text-ink-3">{writeback.type}</p>
              <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap rounded-lg bg-canvas p-3 text-sm text-ink-2">
                {writeback.content}
              </pre>
              {writeback.accepted_asset_id ? (
                <p className="mt-2 font-mono text-xs text-emerald-600">
                  {zh ? "已接受资产" : "Accepted asset"}: {writeback.accepted_asset_id}
                </p>
              ) : null}
            </Card>
          ))}
        </div>
      ) : (
        <Card className="mt-3 p-5 text-sm text-ink-3">{zh ? "无写回。" : "No writebacks recorded."}</Card>
      )}

      <SectionLabel>{zh ? "时间线" : "Timeline"}</SectionLabel>
      {audit.events.length ? (
        <Card className="mt-3 divide-y divide-edge-1">
          {audit.events.map((event) => (
            <div key={event.id} className="px-5 py-3.5">
              <div className="flex items-center justify-between gap-3">
                <span className="font-mono text-sm font-semibold text-ink">{event.event_type}</span>
                <span className="text-xs text-ink-3">{relativeTime(event.created_at, lang)}</span>
              </div>
              <pre className="mt-2 max-h-40 overflow-auto rounded-lg bg-canvas p-3 text-xs text-ink-2">
                {JSON.stringify(event.payload, null, 2)}
              </pre>
            </div>
          ))}
        </Card>
      ) : (
        <Card className="mt-3 p-5 text-sm text-ink-3">{zh ? "无事件。" : "No events recorded."}</Card>
      )}
    </Page>
  );
}
