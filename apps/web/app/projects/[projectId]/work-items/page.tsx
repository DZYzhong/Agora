import Link from "next/link";
import { apiGet } from "../../../../lib/api";
import { currentLang } from "../../../../lib/i18n";
import { relativeTime } from "../../../../lib/format";
import { Badge, EmptyState, Page, PageHeader, Table } from "../../../../components/ui";

type ContextState = {
  session_id: string;
  event_type: string;
  context_pack_id: string | null;
  provisional: boolean;
  freshness: {
    context_coverage?: string;
    recommended_action?: string;
    observed_commit_sha?: string | null;
  };
  budget: { estimated_tokens?: number; token_budget?: number } | null;
  created_at: string;
};

type WorkItem = {
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
};

function statusTone(status: string) {
  if (status === "completed" || status === "accepted") return "green" as const;
  if (status === "failed" || status === "blocked") return "red" as const;
  if (status === "in_progress" || status === "started") return "blue" as const;
  return "slate" as const;
}

export default async function WorkItemsPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  const lang = await currentLang();
  const zh = lang === "zh";

  let workItems: WorkItem[] = [];
  try {
    workItems = await apiGet<WorkItem[]>(`/projects/${projectId}/work-items`);
  } catch {
    workItems = [];
  }

  return (
    <Page>
      <PageHeader
        title={zh ? "工作项" : "Work items"}
        subtitle={
          zh
            ? "从 AI 工具会话与工作流活动中识别的团队任务"
            : "Team tasks detected from AI tool sessions and project workflow activity."
        }
        meta={
          <span className="rounded-full bg-surface px-3 py-1 text-sm text-ink-2 ring-1 ring-inset ring-edge">
            {workItems.length}
          </span>
        }
        actions={
          <Link href={`/projects/${projectId}`} className="rounded-lg border border-slate-300 bg-surface px-3 py-1.5 text-sm font-medium text-ink shadow-sm hover:bg-canvas">
            ← {zh ? "返回项目" : "Back to project"}
          </Link>
        }
      />

      {workItems.length === 0 ? (
        <EmptyState
          title={zh ? "还没有工作项" : "No work items yet"}
          hint={
            zh
              ? "当 AI 工具开始为该项目的任务工作时，Agora 会识别并展示在这里。"
              : "When an AI tool starts work for this project, Agora will identify the task and show it here."
          }
        />
      ) : (
        <section className="mt-6 overflow-hidden rounded-2xl border border-edge bg-surface shadow-sm">
          <Table
            headers={[
              zh ? "任务" : "Task",
              zh ? "状态" : "Status",
              zh ? "会话" : "Sessions",
              zh ? "上下文" : "Context",
              zh ? "参与者" : "Participants",
            ]}
          >
            {workItems.map((item) => {
              const state = item.latest_context_state;
              return (
                <tr
                  key={item.id}
                  className="cursor-pointer transition hover:bg-canvas"
                  onClick={undefined}
                >
                  <td className="px-5 py-3.5">
                    <Link
                      href={`/projects/${projectId}/work-items/${item.id}`}
                      className="block"
                    >
                      <span className="font-medium text-ink hover:text-blue-700">
                        {item.external_key ? `${item.external_key} · ${item.title}` : item.title}
                      </span>
                      <span className="mt-0.5 block max-w-xl truncate text-xs text-ink-3">
                        {item.description ?? item.source}
                      </span>
                    </Link>
                  </td>
                  <td className="px-5 py-3.5">
                    <Badge tone={statusTone(item.status)}>{item.status}</Badge>
                    <span className="mt-0.5 block text-xs text-ink-3">{item.stage}</span>
                  </td>
                  <td className="px-5 py-3.5 text-ink">{item.session_count}</td>
                  <td className="px-5 py-3.5">
                    <Link
                      href={`/projects/${projectId}/work-items/${item.id}`}
                      className="block max-w-xs"
                    >
                      <span className="font-medium text-ink">
                        {state
                          ? `${state.provisional ? (zh ? "临时" : "Provisional") + " · " : ""}${
                              state.freshness.context_coverage ?? "unknown"
                            }`
                          : zh
                            ? "无上下文"
                            : "No context"}
                      </span>
                      <span className="mt-0.5 block text-xs text-ink-3">
                        {state
                          ? relativeTime(state.created_at, lang)
                          : zh
                            ? "AI 工具尚未上传上下文"
                            : "AI tool has not uploaded context yet"}
                      </span>
                    </Link>
                  </td>
                  <td className="px-5 py-3.5 text-ink-2">
                    {item.participants.length === 0
                      ? zh
                        ? "无"
                        : "None"
                      : item.participants.length === 1
                        ? "1"
                        : String(item.participants.length)}
                  </td>
                </tr>
              );
            })}
          </Table>
        </section>
      )}
    </Page>
  );
}
