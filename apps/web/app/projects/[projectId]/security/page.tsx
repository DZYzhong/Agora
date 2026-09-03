import { apiGet } from "../../../../lib/api";
import { currentLang } from "../../../../lib/i18n";
import { relativeTime } from "../../../../lib/format";
import { Badge, Card, EmptyState, Page, PageHeader, Table } from "../../../../components/ui";

type SecurityAuditEvent = {
  id: string;
  actor_user_id: string;
  actor_credential_kind: string;
  action: string;
  target_type: string;
  target_id: string;
  decision: string;
  reason: string | null;
  created_at: string;
};

function decisionTone(decision: string) {
  if (decision === "allow") return "green" as const;
  if (decision === "deny") return "red" as const;
  return "amber" as const;
}

export default async function ProjectSecurityPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  const lang = await currentLang();
  const zh = lang === "zh";

  let events: SecurityAuditEvent[] = [];
  try {
    events = await apiGet<SecurityAuditEvent[]>(`/projects/${projectId}/security-audit`);
  } catch {
    events = [];
  }

  return (
    <Page>
      <PageHeader
        title={zh ? "安全审计" : "Security audit"}
        subtitle={zh ? "本项目的敏感治理决策。" : "Sensitive governance decisions for this project."}
        meta={
          <span className="rounded-full bg-surface px-3 py-1 text-sm text-ink-2 ring-1 ring-inset ring-edge">
            {events.length}
          </span>
        }
      />

      {events.length === 0 ? (
        <EmptyState
          title={zh ? "暂无审计事件" : "No security audit events recorded"}
          hint={zh ? "敏感治理操作会在此留下记录。" : "Sensitive governance operations will be recorded here."}
        />
      ) : (
        <Card className="mt-6">
          <Table
            headers={[
              zh ? "决策" : "Decision",
              zh ? "动作" : "Action",
              zh ? "主体" : "Actor",
              zh ? "目标" : "Target",
              zh ? "原因" : "Reason",
              zh ? "时间" : "When",
            ]}
          >
            {events.map((event) => (
              <tr key={event.id} className="align-top transition hover:bg-canvas">
                <td className="px-5 py-3">
                  <Badge tone={decisionTone(event.decision)}>{event.decision}</Badge>
                </td>
                <td className="px-5 py-3">
                  <span className="font-mono text-xs text-ink">{event.action}</span>
                </td>
                <td className="px-5 py-3">
                  <span className="text-xs text-ink-2">{event.actor_credential_kind}</span>
                  <span className="mt-0.5 block font-mono text-[11px] text-ink-3">
                    {event.actor_user_id}
                  </span>
                </td>
                <td className="px-5 py-3">
                  <span className="text-xs text-ink-2">{event.target_type}</span>
                  <span className="mt-0.5 block font-mono text-[11px] text-ink-3">
                    {event.target_id}
                  </span>
                </td>
                <td className="max-w-xs px-5 py-3 text-xs text-ink-2">
                  {event.reason ?? "—"}
                </td>
                <td className="whitespace-nowrap px-5 py-3 text-xs text-ink-3">
                  {relativeTime(event.created_at, lang)}
                </td>
              </tr>
            ))}
          </Table>
        </Card>
      )}
    </Page>
  );
}
