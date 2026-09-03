import Link from "next/link";
import { apiGet } from "../../../../../lib/api";
import { currentLang } from "../../../../../lib/i18n";
import { relativeTime } from "../../../../../lib/format";
import { Badge, Card, EmptyState, Page, PageHeader, SectionLabel } from "../../../../../components/ui";

type ContextState = {
  session_id: string;
  event_type: string;
  context_pack_id: string | null;
  provisional: boolean;
  freshness: {
    repository_relation?: string;
    workspace_state?: string;
    context_coverage?: string;
    proposal_state?: string;
    accepted_revision_id?: string | null;
    observed_commit_sha?: string | null;
    recommended_action?: string;
  };
  budget: { estimated_tokens?: number; token_budget?: number; included_assets?: number } | null;
  created_at: string;
};

type WorkSession = {
  id: string;
  task_id: string | null;
  agent_type: string;
  intent: string;
  status: string;
  created_at: string;
  closed_at: string | null;
  audit_counts: { events: number; context_states: number; development_updates: number };
};

type WorkArtifact = {
  id: string;
  session_id: string;
  step_key: string;
  type: string;
  title: string;
  content: string;
  metadata: Record<string, unknown>;
  created_by_user_id: string;
  created_at: string;
};

type HumanConfirmation = {
  id: string;
  session_id: string;
  step_key: string;
  confirmation_type: string;
  decision: string;
  comment: string | null;
  confirmed_by_user_id: string;
  created_at: string;
};

type WorkflowStep = {
  id: string;
  step_key: string;
  title: string;
  order_index: number;
  status: string;
  required_artifacts: Array<{ type?: string }>;
  artifacts: WorkArtifact[];
  human_confirmations: HumanConfirmation[];
};

type WorkflowExecution = {
  id: string;
  workflow_version_id: string;
  status: string;
  current_step_key: string | null;
  steps: WorkflowStep[];
};

type WorkItemDetail = {
  id: string;
  external_key: string | null;
  title: string;
  description: string | null;
  status: string;
  stage: string;
  source: string;
  session_count: number;
  participants: string[];
  latest_context_state: ContextState | null;
  capability_pins: {
    context_revision_id: string | null;
    workflow_version_id: string | null;
    skill_version_id: string | null;
  };
  workflow_execution: WorkflowExecution | null;
  sessions: WorkSession[];
};

function formatPin(value: string | null, zh: boolean): string {
  return value ?? (zh ? "未固定" : "Not pinned");
}

function stepStatusClass(status: string): "green" | "blue" | "slate" | "amber" {
  if (status === "completed") return "green";
  if (status === "running") return "blue";
  if (status === "waiting" || status === "pending") return "slate";
  return "amber";
}

function stepMarker(status: string): string {
  if (status === "completed") return "✓";
  if (status === "running") return "●";
  return "○";
}

function metadataLabel(metadata: Record<string, unknown>): string {
  const path = metadata.path;
  if (typeof path === "string" && path.length > 0) return path;
  const keys = Object.keys(metadata);
  return keys.length ? keys.join(", ") : "—";
}

const dt = "text-xs text-slate-400";
const dd = "text-slate-700";

export default async function WorkItemDetailPage({
  params,
}: {
  params: Promise<{ projectId: string; workItemId: string }>;
}) {
  const { projectId, workItemId } = await params;
  const lang = await currentLang();
  const zh = lang === "zh";

  let item: WorkItemDetail | null = null;
  try {
    item = await apiGet<WorkItemDetail>(`/projects/${projectId}/work-items/${workItemId}`);
  } catch {
    item = null;
  }

  if (!item) {
    return (
      <Page>
        <PageHeader title={zh ? "工作项" : "Work item"} />
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {zh ? "工作项不存在。" : "Work item not found."}
        </div>
        <p className="mt-4">
          <Link href={`/projects/${projectId}/work-items`} className="text-sm font-medium text-blue-600 hover:text-blue-700">
            ← {zh ? "返回工作项列表" : "Back to work items"}
          </Link>
        </p>
      </Page>
    );
  }

  const context = item.latest_context_state;
  const execution = item.workflow_execution;

  return (
    <Page>
      <PageHeader
        title={item.external_key ? `${item.external_key} · ${item.title}` : item.title}
        subtitle={item.description ?? (zh ? "由 AI 工具工作会话跟踪。" : "Tracked from AI tool work sessions.")}
        meta={<Badge tone={item.status === "completed" ? "green" : item.status === "failed" ? "red" : "blue"}>{item.status}</Badge>}
        actions={
          <Link
            href={`/projects/${projectId}/work-items`}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
          >
            ← {zh ? "工作项列表" : "Work items"}
          </Link>
        }
      />

      <section className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="p-5">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
            {zh ? "任务状态" : "Task state"}
          </p>
          <p className="mt-1 text-sm text-slate-500">{item.source}</p>
          <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
            <div>
              <dt className={dt}>{zh ? "阶段" : "Stage"}</dt>
              <dd className={dd}>{item.stage}</dd>
            </div>
            <div>
              <dt className={dt}>{zh ? "会话" : "Sessions"}</dt>
              <dd className={dd}>{item.session_count}</dd>
            </div>
            <div className="col-span-2">
              <dt className={dt}>{zh ? "参与者" : "Participants"}</dt>
              <dd className="truncate">{item.participants.length ? item.participants.join(", ") : "—"}</dd>
            </div>
          </dl>
        </Card>
        <Card className="p-5 sm:col-span-1 lg:col-span-3">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
            {zh ? "最近上下文状态" : "Latest context state"}
          </p>
          {context ? (
            <>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <Badge tone={context.provisional ? "amber" : "green"} dot={false}>
                  {context.provisional ? (zh ? "临时" : "provisional") : zh ? "已接受" : "accepted"}
                </Badge>
                <span className="font-mono text-xs text-slate-400">
                  {context.event_type} · {context.context_pack_id ?? "no pack id"}
                </span>
              </div>
              <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm lg:grid-cols-4">
                <div>
                  <dt className={dt}>{zh ? "覆盖度" : "Coverage"}</dt>
                  <dd className={dd}>{context.freshness.context_coverage ?? "unknown"}</dd>
                </div>
                <div>
                  <dt className={dt}>{zh ? "建议动作" : "Recommended action"}</dt>
                  <dd className="truncate font-mono text-xs">{context.freshness.recommended_action ?? "review_context"}</dd>
                </div>
                <div>
                  <dt className={dt}>{zh ? "观察 commit" : "Observed commit"}</dt>
                  <dd className="truncate font-mono text-xs">
                    {context.freshness.observed_commit_sha ?? (zh ? "未记录" : "Not recorded")}
                  </dd>
                </div>
                <div>
                  <dt className={dt}>{zh ? "估算 tokens" : "Estimated tokens"}</dt>
                  <dd className={dd}>{context.budget?.estimated_tokens ?? "?"}</dd>
                </div>
              </dl>
              <p className="mt-2 text-xs text-slate-400">
                {zh ? "更新于" : "Updated"}{" "}
                <time dateTime={context.created_at}>{relativeTime(context.created_at, lang)}</time>
              </p>
            </>
          ) : (
            <p className="mt-2 text-sm text-slate-400">
              {zh ? "AI 工具尚未为此工作项上传上下文。" : "No AI tool has uploaded context for this work item yet."}
            </p>
          )}
        </Card>
      </section>

      <Card className="mt-4 p-5">
        <h2 className="text-sm font-semibold text-slate-900">{zh ? "能力固定" : "Capability pins"}</h2>
        <dl className="mt-3 grid grid-cols-1 gap-2 text-sm sm:grid-cols-3">
          <div>
            <dt className={dt}>{zh ? "上下文修订" : "Context revision"}</dt>
            <dd className="truncate font-mono text-xs">{formatPin(item.capability_pins.context_revision_id, zh)}</dd>
          </div>
          <div>
            <dt className={dt}>{zh ? "工作流版本" : "Workflow version"}</dt>
            <dd className="truncate font-mono text-xs">{formatPin(item.capability_pins.workflow_version_id, zh)}</dd>
          </div>
          <div>
            <dt className={dt}>{zh ? "技能版本" : "Skill version"}</dt>
            <dd className="truncate font-mono text-xs">{formatPin(item.capability_pins.skill_version_id, zh)}</dd>
          </div>
        </dl>
      </Card>

      <SectionLabel>{zh ? "工作流审计" : "Workflow audit"}</SectionLabel>
      {execution ? (
        <>
          <div
            className="stepper mt-3 flex items-center gap-2 overflow-x-auto rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm"
            aria-label="Workflow progress"
          >
            {[...execution.steps]
              .sort((a, b) => a.order_index - b.order_index)
              .map((step, index, sorted) => (
                <div key={step.id} className="flex shrink-0 items-center gap-2">
                  <span className="flex items-center gap-1.5">
                    <span
                      className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${
                        stepStatusClass(step.status) === "green"
                          ? "bg-emerald-100 text-emerald-700"
                          : stepStatusClass(step.status) === "blue"
                            ? "bg-blue-100 text-blue-700"
                            : stepStatusClass(step.status) === "amber"
                              ? "bg-amber-100 text-amber-700"
                              : "bg-slate-100 text-slate-400"
                      }`}
                      aria-hidden="true"
                    >
                      {stepMarker(step.status)}
                    </span>
                    <span
                      className={`text-sm font-medium ${
                        stepStatusClass(step.status) === "green"
                          ? "text-slate-900"
                          : stepStatusClass(step.status) === "blue"
                            ? "text-blue-700"
                            : "text-slate-400"
                      }`}
                    >
                      {step.title}
                    </span>
                  </span>
                  {index < sorted.length - 1 ? (
                    <span className="h-px w-6 bg-slate-200" aria-hidden="true" />
                  ) : null}
                </div>
              ))}
          </div>

          <div className="mt-4 space-y-4">
            {execution.steps.map((step) => (
              <Card key={step.id} className="p-5">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h3 className="text-[15px] font-semibold text-slate-900">{step.title}</h3>
                    <p className="mt-0.5 font-mono text-xs text-slate-400">{step.step_key}</p>
                  </div>
                  <Badge tone={stepStatusClass(step.status) as "green" | "blue" | "amber" | "slate"}>
                    {step.status}
                  </Badge>
                </div>
                <dl className="mt-3 grid grid-cols-3 gap-2 border-t border-slate-100 pt-3 text-sm">
                  <div>
                    <dt className={dt}>{zh ? "必需产物" : "Required outputs"}</dt>
                    <dd className="truncate">
                      {step.required_artifacts.map((artifact) => artifact.type ?? "artifact").join(", ") || "—"}
                    </dd>
                  </div>
                  <div>
                    <dt className={dt}>{zh ? "步骤产物" : "Step outputs"}</dt>
                    <dd className={dd}>{step.artifacts.length}</dd>
                  </div>
                  <div>
                    <dt className={dt}>{zh ? "人工确认" : "Human confirmations"}</dt>
                    <dd className={dd}>{step.human_confirmations.length}</dd>
                  </div>
                </dl>

                {step.artifacts.length ? (
                  <div className="mt-3 space-y-2">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                      {zh ? "步骤产物" : "Step outputs"}
                    </p>
                    {step.artifacts.map((artifact) => (
                      <div key={artifact.id} className="rounded-xl border border-slate-100 bg-slate-50/60 p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <p className="text-sm font-semibold text-slate-800">{artifact.title}</p>
                            <p className="mt-0.5 font-mono text-xs text-slate-400">
                              {artifact.type} · {metadataLabel(artifact.metadata)}
                            </p>
                          </div>
                          <span className="shrink-0 text-xs text-slate-400">
                            {relativeTime(artifact.created_at, lang)}
                          </span>
                        </div>
                        <p className="mt-2 whitespace-pre-wrap text-sm text-slate-600">{artifact.content}</p>
                      </div>
                    ))}
                  </div>
                ) : null}

                {step.human_confirmations.length ? (
                  <div className="mt-3 space-y-2">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                      {zh ? "人工确认" : "Human confirmations"}
                    </p>
                    {step.human_confirmations.map((confirmation) => (
                      <div key={confirmation.id} className="rounded-xl border border-slate-100 bg-slate-50/60 p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <Badge tone={confirmation.decision === "approved" ? "green" : confirmation.decision === "rejected" ? "red" : "amber"} dot={false}>
                              {confirmation.decision}
                            </Badge>
                            <p className="mt-1 font-mono text-xs text-slate-400">
                              {confirmation.confirmation_type} · {confirmation.confirmed_by_user_id}
                            </p>
                          </div>
                          <span className="shrink-0 text-xs text-slate-400">
                            {relativeTime(confirmation.created_at, lang)}
                          </span>
                        </div>
                        <p className="mt-2 text-sm text-slate-600">{confirmation.comment ?? (zh ? "无评论" : "No comment")}</p>
                      </div>
                    ))}
                  </div>
                ) : null}
              </Card>
            ))}
          </div>
        </>
      ) : (
        <Card className="mt-3 p-5 text-sm text-slate-400">
          {zh ? "此工作项尚未创建工作流执行。" : "No workflow execution has been created for this work item."}
        </Card>
      )}

      <SectionLabel>{zh ? "工作会话" : "Work sessions"}</SectionLabel>
      {item.sessions.length ? (
        <div className="mt-3 grid gap-4 lg:grid-cols-2">
          {item.sessions.map((session) => (
            <Card key={session.id} className="p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="truncate text-[15px] font-semibold text-slate-900">{session.intent}</h3>
                  <p className="mt-0.5 truncate font-mono text-xs text-slate-400">
                    {session.agent_type} · {session.id}
                  </p>
                </div>
                <Badge tone={session.status === "closed" ? "slate" : session.status === "failed" ? "red" : "green"}>
                  {session.status}
                </Badge>
              </div>
              <dl className="mt-3 grid grid-cols-2 gap-2 border-t border-slate-100 pt-3 text-sm">
                <div>
                  <dt className={dt}>{zh ? "开始" : "Started"}</dt>
                  <dd className={dd}>{relativeTime(session.created_at, lang)}</dd>
                </div>
                <div>
                  <dt className={dt}>{zh ? "关闭" : "Closed"}</dt>
                  <dd className={dd}>{session.closed_at ? relativeTime(session.closed_at, lang) : zh ? "进行中" : "Open"}</dd>
                </div>
                <div>
                  <dt className={dt}>{zh ? "上下文状态" : "Context states"}</dt>
                  <dd className={dd}>{session.audit_counts.context_states}</dd>
                </div>
                <div>
                  <dt className={dt}>Events</dt>
                  <dd className={dd}>{session.audit_counts.events}</dd>
                </div>
              </dl>
              <Link
                href={`/projects/${projectId}/sessions/${session.id}`}
                className="mt-3 inline-block text-sm font-medium text-blue-600 hover:text-blue-700"
              >
                {zh ? "查看会话审计" : "View session audit"} →
              </Link>
            </Card>
          ))}
        </div>
      ) : (
        <EmptyState title={zh ? "暂无会话" : "No sessions recorded"} />
      )}
    </Page>
  );
}
