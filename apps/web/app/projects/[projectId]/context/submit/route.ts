import { redirect } from "next/navigation";

export async function POST(request: Request, { params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const formData = await request.formData();
  const query = String(formData.get("query") ?? "").trim();
  const tokenBudget = String(formData.get("token_budget") ?? "1200").trim();

  const searchParams = new URLSearchParams();
  if (query) {
    searchParams.set("query", query);
  }
  if (tokenBudget) {
    searchParams.set("token_budget", tokenBudget);
  }

  redirect(`/projects/${projectId}/context?${searchParams.toString()}`);
}
