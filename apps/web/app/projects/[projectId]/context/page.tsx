import { apiGet, apiPost } from "../../../../lib/api";

type Project = {
  id: string;
  name: string;
  slug: string;
  git_remotes: string[];
};

type StartWorkResponse = {
  session_id: string;
  intent: string;
};

type ContextResponse = {
  id: string;
  summary: string;
  source_refs: Array<{
    asset_id: string;
    title: string;
    source_uri: string;
    relevance: number;
    retrieval_sources: string[];
  }>;
};

export default async function ContextTesterPage({
  params,
  searchParams,
}: {
  params: Promise<{ projectId: string }>;
  searchParams: Promise<{ query?: string; token_budget?: string }>;
}) {
  const { projectId } = await params;
  const { query = "", token_budget: tokenBudgetParam = "1200" } = await searchParams;
  const project = await apiGet<Project>(`/projects/${projectId}`);
  const tokenBudget = Number.parseInt(tokenBudgetParam, 10) || 1200;
  let context: ContextResponse | null = null;
  let session: StartWorkResponse | null = null;
  let error: string | null = null;

  if (query.trim()) {
    try {
      session = await apiPost<StartWorkResponse>("/harness/start-work", {
        project_id: project.id,
        user_message: `${project.name} ${project.slug} ${query}`,
        repo_remote: project.git_remotes[0] ?? null,
        agent_type: "web-context-tester",
      });
      context = await apiPost<ContextResponse>("/harness/plan-context", {
        session_id: session.session_id,
        query,
        token_budget: tokenBudget,
      });
    } catch (caught) {
      error = caught instanceof Error ? caught.message : "Context query failed";
    }
  }

  return (
    <main className="page">
      <h1>Context Tester</h1>
      <p className="muted">{project.name} / {project.slug}</p>
      <form className="panel form" action={`/projects/${project.id}/context/submit`} method="post">
        <h2>Plan context</h2>
        {error ? <p className="alert">{error}</p> : null}
        <label>
          Query
          <input name="query" defaultValue={query} placeholder="核心模块、主要业务流程和潜在风险" required />
        </label>
        <label>
          Token budget
          <input name="token_budget" defaultValue={String(tokenBudget)} inputMode="numeric" />
        </label>
        <button type="submit">Run context query</button>
      </form>
      {context ? (
        <section className="context-result">
          <div className="panel">
            <p className="eyebrow">Session</p>
            <h2>{session?.intent ?? "analysis"}</h2>
            <p className="muted">{session?.session_id}</p>
          </div>
          <div className="panel">
            <p className="eyebrow">Summary</p>
            <pre className="context-summary">{context.summary}</pre>
          </div>
          <section className="source-list" aria-label="Context source references">
            <div className="source-row source-header">
              <span>Source</span>
              <span>Retrieval</span>
              <span>Score</span>
            </div>
            {context.source_refs.map((source) => (
              <div className="source-row" key={source.asset_id}>
                <div>
                  <strong className="asset-title">{source.title}</strong>
                  <p className="asset-uri">{source.source_uri}</p>
                </div>
                <span className="asset-type">{source.retrieval_sources.join(" / ")}</span>
                <span className="source-score">{source.relevance.toFixed(2)}</span>
              </div>
            ))}
          </section>
        </section>
      ) : null}
    </main>
  );
}
