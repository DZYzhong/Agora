"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { apiPost } from "../../lib/api";

type Project = {
  id: string;
};

export async function createProject(formData: FormData) {
  const name = String(formData.get("name") ?? "").trim();
  const slug = String(formData.get("slug") ?? "").trim();
  const orgId = String(formData.get("org_id") ?? "local-org").trim();
  const gitRemote = String(formData.get("git_remote") ?? "").trim();

  const project = await apiPost<Project>("/projects", {
    org_id: orgId,
    name,
    slug,
    git_remotes: gitRemote ? [gitRemote] : [],
  });

  revalidatePath("/projects");
  redirect(`/projects/${project.id}`);
}

export async function initializeProject(projectId: string, formData: FormData) {
  const repoPath = String(formData.get("repo_path") ?? "").trim();

  let initError: string | null = null;
  try {
    await apiPost(`/projects/${projectId}/initialize-local`, {
      repo_path: repoPath,
    });
  } catch (error) {
    initError = error instanceof Error ? error.message : "Initialize failed";
  }

  if (initError) {
    redirect(`/projects/${projectId}?init_error=${encodeURIComponent(initError)}`);
  }

  revalidatePath(`/projects/${projectId}`);
  revalidatePath(`/projects/${projectId}/assets`);
  redirect(`/projects/${projectId}/assets`);
}
