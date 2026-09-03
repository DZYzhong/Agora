import Link from "next/link";
import { currentLang } from "../lib/i18n";

export default async function Home() {
  const lang = await currentLang();
  const zh = lang === "zh";

  const cards = [
    {
      href: "/projects",
      mono: "WI",
      tint: "bg-blue-50 text-blue-600",
      title: zh ? "项目与工作项" : "Projects & work items",
      hint: zh
        ? "创建项目并查看团队 AI 工具产出的工作项、会话与上下文。"
        : "Create projects and review what team AI tools have produced.",
    },
    {
      href: "/projects",
      mono: "SE",
      tint: "bg-emerald-50 text-emerald-600",
      title: zh ? "AI 会话" : "Harness sessions",
      hint: zh
        ? "追踪 Agent 如何解析项目上下文并运行技能。"
        : "Trace how agents resolve project context and run skills.",
    },
    {
      href: "/projects",
      mono: "WB",
      tint: "bg-violet-50 text-violet-600",
      title: zh ? "知识沉淀" : "Knowledge & writebacks",
      hint: zh
        ? "审阅 AI 生成的知识草稿，沉淀为项目资产。"
        : "Review AI-generated knowledge before it is accepted into the project.",
    },
  ];

  return (
    <main className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
      <div className="text-center">
        <span className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-600 text-2xl font-bold text-white shadow-sm">
          A
        </span>
        <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
          {zh ? "团队 AI 项目协作台" : "Team AI Project Harness"}
        </h1>
        <p className="mx-auto mt-3 max-w-2xl text-sm leading-relaxed text-slate-500">
          {zh
            ? "Agora 管理 AI 工具在团队项目中的工作：上下文、审批、质量证据与知识沉淀都在同一个治理界面中。"
            : "Agora governs how AI tools work inside team projects — context, approvals, quality evidence and knowledge — in one place."}
        </p>
        <Link
          href="/projects"
          className="mt-6 inline-block rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700"
        >
          {zh ? "进入项目 →" : "Open projects →"}
        </Link>
      </div>

      <section className="mt-14 grid gap-4 sm:grid-cols-3">
        {cards.map((card) => (
          <Link
            key={card.mono}
            href={card.href}
            className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-px hover:border-blue-200 hover:shadow"
          >
            <span
              className={`flex h-9 w-9 items-center justify-center rounded-lg text-xs font-bold ${card.tint}`}
            >
              {card.mono}
            </span>
            <span className="mt-3 block text-[15px] font-semibold text-slate-900 group-hover:text-blue-700">
              {card.title} →
            </span>
            <span className="mt-1 block text-xs leading-relaxed text-slate-400">{card.hint}</span>
          </Link>
        ))}
      </section>
    </main>
  );
}
