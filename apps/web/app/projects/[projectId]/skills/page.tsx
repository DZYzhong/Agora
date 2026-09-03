import Link from "next/link";
import { apiGet } from "../../../../lib/api";
import { currentLang } from "../../../../lib/i18n";
import { relativeTime } from "../../../../lib/format";
import { Badge, Card, EmptyState, Page, PageHeader, SectionLabel } from "../../../../components/ui";

type Skill = {
  id: string;
  slug: string;
  name: string;
  status: string;
  definition: {
    version?: string;
    summary?: string;
    triggers?: string[];
    input_schema?: Record<string, unknown>;
    instructions?: string;
    risk_constraints?: string[];
    builtin?: boolean;
  };
  current_version_id: string | null;
  current_version: {
    id: string;
    version: string;
    status: string;
    approved_by_user_id: string | null;
    created_at: string;
  } | null;
  evidence_refs: Array<{
    id: string;
    type: string;
    title: string;
    status: string;
    accepted_asset_id: string | null;
    content_preview: string;
  }>;
  builtin: boolean;
};

type SkillRun = {
  id: string;
  skill_id: string;
  skill_version_id: string | null;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  warnings: string[];
  status: string;
  created_at: string;
};

const inputClass =
  "w-full rounded-lg border border-slate-300 bg-surface px-3 py-2 text-sm shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100";
const labelClass = "mb-1 block text-xs font-medium text-ink-2";

function statusTone(status: string) {
  if (status === "approved") return "green" as const;
  if (status === "candidate" || status === "draft") return "amber" as const;
  if (status === "deprecated") return "slate" as const;
  return "blue" as const;
}

export default async function SkillsPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  const lang = await currentLang();
  const zh = lang === "zh";

  let skills: Skill[] = [];
  let runs: SkillRun[] = [];
  try {
    [skills, runs] = await Promise.all([
      apiGet<Skill[]>(`/projects/${projectId}/skills`),
      apiGet<SkillRun[]>(`/projects/${projectId}/skill-runs`),
    ]);
  } catch {
    skills = [];
    runs = [];
  }
  const skillNames = new Map(skills.map((skill) => [skill.id, skill.name]));

  return (
    <Page>
      <PageHeader
        title={zh ? "技能" : "Skills"}
        subtitle={zh ? "内置与项目技能及运行记录" : "Built-in and project skills with run history"}
        meta={
          <span className="rounded-full bg-surface px-3 py-1 text-sm text-ink-2 ring-1 ring-inset ring-edge">
            {skills.length}
          </span>
        }
      />

      <Card className="mt-6 p-5">
        <div className="flex items-center gap-2">
          <span className="flex h-6 w-6 items-center justify-center rounded-md bg-blue-50 text-blue-600">
            <svg viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5" aria-hidden="true">
              <path d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z" />
            </svg>
          </span>
          <h2 className="text-sm font-semibold text-ink">{zh ? "创建技能候选" : "Create skill candidate"}</h2>
        </div>
        <form
          action={`/projects/${projectId}/skills/create`}
          method="post"
          className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4"
        >
          <label className="block">
            <span className={labelClass}>Slug</span>
            <input name="slug" placeholder="release-risk-review" required className={inputClass} />
          </label>
          <label className="block">
            <span className={labelClass}>{zh ? "名称" : "Name"}</span>
            <input name="name" placeholder="Release Risk Review" required className={inputClass} />
          </label>
          <label className="block">
            <span className={labelClass}>Version</span>
            <input name="version" defaultValue="0.1.0" className={inputClass} />
          </label>
          <label className="block">
            <span className={labelClass}>{zh ? "触发词" : "Triggers"}</span>
            <input name="triggers" placeholder="release, risk, rollback" className={inputClass} />
          </label>
          <label className="block sm:col-span-2 lg:col-span-4">
            <span className={labelClass}>{zh ? "指令" : "Instructions"}</span>
            <textarea
              name="instructions"
              rows={2}
              placeholder={
                zh ? "评审发布风险并给出简洁结论。" : "Review release risk and produce concise findings."
              }
              required
              className={inputClass}
            />
          </label>
          <button
            type="submit"
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 lg:col-start-4"
          >
            {zh ? "创建候选" : "Create candidate"}
          </button>
        </form>
      </Card>

      <SectionLabel>{zh ? "技能" : "Skills"}</SectionLabel>
      {skills.length === 0 ? (
        <EmptyState
          title={zh ? "还没有技能" : "No skills yet"}
          hint={zh ? "创建技能候选后会显示在这里。" : "Create a skill candidate to get started."}
        />
      ) : (
        <section className="mt-3 grid gap-4 lg:grid-cols-2">
          {skills.map((skill) => (
            <Card key={skill.id} className="flex flex-col">
              <div className="flex items-start justify-between gap-3 border-b border-edge-1 px-5 py-4">
                <div className="min-w-0">
                  <p className="text-xs font-medium text-ink-3">
                    {skill.builtin ? (zh ? "内置" : "Built-in") : zh ? "项目技能" : "Project skill"}
                  </p>
                  <h3 className="mt-0.5 truncate text-[15px] font-semibold text-ink">{skill.name}</h3>
                  <p className="mt-0.5 truncate font-mono text-xs text-ink-3">{skill.slug}</p>
                </div>
                <Badge tone={statusTone(skill.status)}>{skill.status}</Badge>
              </div>
              <dl className="grid grid-cols-2 gap-x-4 gap-y-2 px-5 py-4 text-sm">
                <div>
                  <dt className="text-xs text-ink-3">Version</dt>
                  <dd className="text-ink">{skill.definition.version ?? (zh ? "未设置" : "Not set")}</dd>
                </div>
                <div>
                  <dt className="text-xs text-ink-3">{zh ? "当前版本" : "Current version"}</dt>
                  <dd className="text-ink">
                    {skill.current_version
                      ? `${skill.current_version.version} · ${skill.current_version.status}`
                      : zh
                        ? "未批准"
                        : "Not approved"}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-ink-3">{zh ? "触发词" : "Triggers"}</dt>
                  <dd className="truncate text-ink-2">
                    {skill.definition.triggers?.join(", ") || (zh ? "未设置" : "Not set")}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-ink-3">Runs</dt>
                  <dd className="text-ink">
                    {runs.filter((run) => run.skill_id === skill.id).length}
                  </dd>
                </div>
              </dl>
              {skill.definition.instructions ? (
                <p className="line-clamp-2 px-5 pb-2 text-sm text-ink-2">
                  {skill.definition.instructions}
                </p>
              ) : null}
              {!skill.builtin ? (
                <details className="px-5 pb-3">
                  <summary className="cursor-pointer text-xs font-medium text-ink-3 hover:text-ink-2">
                    {zh ? "编辑草稿字段" : "Edit draft fields"}
                  </summary>
                  <form
                    action={`/projects/${projectId}/skills/${skill.id}/update`}
                    method="post"
                    className="mt-3 grid gap-2 sm:grid-cols-2"
                  >
                    <input name="name" defaultValue={skill.name} placeholder="Name" className={inputClass} />
                    <input name="version" defaultValue={skill.definition.version ?? ""} placeholder="Version" className={inputClass} />
                    <input name="triggers" defaultValue={skill.definition.triggers?.join(", ") ?? ""} placeholder="Triggers" className={`${inputClass} sm:col-span-2`} />
                    <textarea name="instructions" rows={2} defaultValue={skill.definition.instructions ?? ""} placeholder="Instructions" className={`${inputClass} sm:col-span-2`} />
                    <select name="status" defaultValue={skill.status} className={inputClass}>
                      <option value="candidate">candidate</option>
                      <option value="draft">draft</option>
                      <option value="approved">approved</option>
                      <option value="deprecated">deprecated</option>
                    </select>
                    <button
                      type="submit"
                      className="rounded-lg bg-slate-800 px-3 py-1.5 text-sm font-semibold text-white hover:bg-slate-700"
                    >
                      {zh ? "保存" : "Save"}
                    </button>
                  </form>
                </details>
              ) : null}
              <div className="mt-auto flex flex-wrap items-center gap-2 border-t border-edge-1 px-5 py-3">
                {!skill.builtin && skill.status !== "approved" ? (
                  <form action={`/projects/${projectId}/skills/${skill.id}/approve`} method="post">
                    <input type="hidden" name="name" defaultValue={skill.name} />
                    <input type="hidden" name="version" defaultValue={skill.definition.version ?? "1.0.0"} />
                    <input type="hidden" name="summary" defaultValue={skill.definition.summary ?? ""} />
                    <input type="hidden" name="triggers" defaultValue={skill.definition.triggers?.join(", ") ?? ""} />
                    <input type="hidden" name="instructions" defaultValue={skill.definition.instructions ?? ""} />
                    <textarea
                      name="risk_constraints"
                      defaultValue={skill.definition.risk_constraints?.join("\n") ?? ""}
                      className="hidden"
                    />
                    <button
                      type="submit"
                      className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-semibold text-white shadow-sm hover:bg-emerald-700"
                    >
                      {zh ? "批准发布" : "Publish approved version"}
                    </button>
                  </form>
                ) : null}
                {!skill.builtin && skill.status !== "deprecated" ? (
                  <form action={`/projects/${projectId}/skills/${skill.id}/deprecate`} method="post">
                    <button
                      type="submit"
                      className="rounded-lg border border-slate-300 bg-surface px-3 py-1.5 text-sm font-medium text-ink-2 hover:text-red-600"
                    >
                      {zh ? "弃用" : "Deprecate"}
                    </button>
                  </form>
                ) : null}
                <form action={`/projects/${projectId}/skills/${skill.id}/run`} method="post" className="flex-1 sm:flex-none">
                  <input
                    name="summary"
                    placeholder={zh ? "本次运行上下文摘要" : "Context summary for this run"}
                    className="w-full rounded-lg border border-slate-300 bg-surface px-3 py-1.5 text-sm shadow-sm outline-none focus:border-blue-500 sm:w-64"
                  />
                  <button
                    type="submit"
                    className="ml-2 rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
                  >
                    {zh ? "运行" : "Run"}
                  </button>
                </form>
              </div>
            </Card>
          ))}
        </section>
      )}

      <SectionLabel>{zh ? "运行记录" : "Skill runs"}</SectionLabel>
      <Card className="mt-3">
        {runs.length ? (
          <div className="divide-y divide-edge-1">
            {runs.map((run) => (
              <div key={run.id} className="px-5 py-3.5">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-semibold text-ink">
                    {skillNames.get(run.skill_id) ?? run.skill_id}
                  </span>
                  <Badge tone={run.status === "failed" ? "red" : run.status === "running" ? "blue" : "slate"}>
                    {run.status}
                  </Badge>
                </div>
                <p className="mt-1 text-xs text-ink-3">
                  {relativeTime(run.created_at, lang)} · SkillVersion {run.skill_version_id ?? (zh ? "未固定" : "not pinned")}
                </p>
                <pre className="mt-2 max-h-40 overflow-auto rounded-lg bg-canvas p-3 text-xs text-ink-2">
                  {JSON.stringify({ input: run.input, output: run.output, warnings: run.warnings }, null, 2)}
                </pre>
              </div>
            ))}
          </div>
        ) : (
          <p className="px-5 py-8 text-center text-sm text-ink-3">
            {zh ? "暂无运行记录。" : "No skill runs recorded."}
          </p>
        )}
      </Card>

      <p className="mt-6">
        <Link href={`/projects/${projectId}`} className="text-sm font-medium text-blue-600 hover:text-blue-700">
          ← {zh ? "返回项目" : "Back to project"}
        </Link>
      </p>
    </Page>
  );
}
