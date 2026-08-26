import { apiGet } from "../../../../lib/api";

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

export default async function ProjectSecurityPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  let events: SecurityAuditEvent[] = [];
  try {
    events = await apiGet<SecurityAuditEvent[]>(`/projects/${projectId}/security-audit`);
  } catch {
    events = [];
  }

  return (
    <main className="page">
      <h1>Security audit</h1>
      <p className="muted">Sensitive governance decisions for this project.</p>
      <section className="panel">
        <div className="history-list">
          <div className="history-row history-header">
            <span>Decision</span>
            <span>Action</span>
            <span>Actor</span>
            <span>Target</span>
            <span>Reason</span>
          </div>
          {events.map((event) => (
            <div className="history-row" key={event.id}>
              <span>{event.decision}</span>
              <span>{event.action}</span>
              <span>
                {event.actor_credential_kind} · {event.actor_user_id}
              </span>
              <span>
                {event.target_type} · {event.target_id}
              </span>
              <span>{event.reason ?? "None"}</span>
            </div>
          ))}
        </div>
        {events.length === 0 ? <p className="muted">No security audit events recorded.</p> : null}
      </section>
    </main>
  );
}
