import { apiGet } from "../../../../lib/api";

type Writeback = {
  id: string;
  type: string;
  title: string;
  content: string;
  status: string;
};

export default async function WritebacksPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  let writebacks: Writeback[] = [];
  try {
    writebacks = await apiGet<Writeback[]>(`/projects/${projectId}/writebacks`);
  } catch {
    writebacks = [];
  }

  return (
    <main className="page">
      <h1>Writebacks</h1>
      <p className="muted">Project {projectId}</p>
      <section className="grid">
        {writebacks.map((writeback) => (
          <div className="panel" key={writeback.id}>
            <h2>{writeback.title}</h2>
            <p className="muted">{writeback.type} / {writeback.status}</p>
            <p>{writeback.content}</p>
          </div>
        ))}
        {writebacks.length === 0 ? (
          <div className="panel">
            <h2>No writebacks</h2>
            <p className="muted">Draft writebacks will appear here after agent work.</p>
          </div>
        ) : null}
      </section>
    </main>
  );
}
