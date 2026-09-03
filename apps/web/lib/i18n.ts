// Lightweight server-side bilingual UI dictionary (zh default, en toggle).
// The app is server-components only, so language is resolved from the
// `agora_lang` cookie on each request; no client i18n runtime is used.
import { cookies } from "next/headers";

export type Lang = "zh" | "en";

export const LANG_COOKIE = "agora_lang";

export async function currentLang(): Promise<Lang> {
  try {
    const store = await cookies();
    const value = store.get(LANG_COOKIE)?.value;
    return value === "en" ? "en" : "zh";
  } catch {
    return "zh";
  }
}

type Dict = Record<string, { zh: string; en: string }>;


// t() resolves one key under a section; sections keep the dictionaries
// readable per page.
export function t(section: string, key: string, lang: Lang): string {
  const entry = DICTIONARY[section]?.[key];
  if (!entry) return key;
  return entry[lang];
}

// Convenience: returns a `t(key)` bound to a section for a page.
export function makeT(section: string, lang: Lang) {
  return (key: string) => t(section, key, lang);
}

// ---------------------------------------------------------------------------
// Dictionary (bilingual strings, grouped by page/section).
// ---------------------------------------------------------------------------
const DICTIONARY: Record<string, Dict> = {
  common: {
    brandName: { zh: "Agora", en: "Agora" },
    brandTagline: { zh: "团队 AI 项目协作台", en: "Team AI Project Harness" },
    signOut: { zh: "退出登录", en: "Sign out" },
    signIn: { zh: "登录", en: "Sign in" },
    projects: { zh: "项目", en: "Projects" },
    users: { zh: "用户", en: "Users" },
    back: { zh: "返回", en: "Back" },
    all: { zh: "全部", en: "All" },
    archive: { zh: "归档", en: "Archive" },
    hideArchived: { zh: "隐藏已归档", en: "Hide archived" },
    showArchived: { zh: "显示已归档", en: "Show archived" },
    noGitRemote: { zh: "无 Git 远端", en: "No Git remote" },
    language: { zh: "中文", en: "English" },
  },
  login: {
    title: { zh: "登录 Agora", en: "Sign in to Agora" },
    subtitle: {
      zh: "使用本地 Agora 账号登录治理界面。Agent 与 CI 工具继续使用 bearer token。",
      en: "Sign in with your local Agora account. Agent and CI tools keep using bearer tokens.",
    },
    username: { zh: "用户名", en: "Username" },
    password: { zh: "密码", en: "Password" },
    submit: { zh: "登录", en: "Sign in" },
    invalid: {
      zh: "用户名或密码错误。审批类操作可能需要重新认证。",
      en: "Invalid username or password. Reauthentication may be required for approval actions.",
    },
    approving: { zh: "正在验证…", en: "Signing in…" },
  },
  projects: {
    title: { zh: "项目", en: "Projects" },
    subtitle: { zh: "团队 AI 治理的项目空间", en: "Configured Agora project spaces." },
    createTitle: { zh: "创建项目", en: "Create project" },
    createSub: {
      zh: "项目空间将由已授权的 AI 工具提供上下文。",
      en: "Context is supplied by authorized AI tools.",
    },
    org: { zh: "组织", en: "Organization" },
    name: { zh: "项目名称", en: "Project name" },
    slug: { zh: "Slug", en: "Slug" },
    gitRemote: { zh: "Git 远端（可选）", en: "Git remote (optional)" },
    create: { zh: "创建", en: "Create" },
    noProjects: { zh: "还没有项目", en: "No projects" },
    noProjectsHint: { zh: "创建项目后，已授权的 AI 工具即可开始贡献上下文。", en: "Create a project to start collecting context from authorized AI tools." },
    statusActive: { zh: "进行中", en: "Active" },
    statusArchived: { zh: "已归档", en: "Archived" },
    count: { zh: "个项目", en: "projects" },
  },
  projectHome: {
    overview: { zh: "概览", en: "Overview" },
    sessions: { zh: "会话", en: "Sessions" },
    allSessions: { zh: "全部会话", en: "All sessions" },
    inFlight: { zh: "进行中的会话", en: "In-flight sessions" },
    inFlightHint: { zh: "当前正在该项目工作的 AI 工具会话。", en: "AI tool sessions currently working on this project." },
    workItems: { zh: "工作项", en: "Work items" },
    workItemsHint: { zh: "跟踪 AI 辅助任务、会话、上下文与审阅流。", en: "Track AI-assisted tasks, sessions, context state, and review flow." },
    status: { zh: "项目状态", en: "Project status" },
    statusHint: { zh: "查看工作项进度、质量证据与待批事项。", en: "Review work item progress, quality evidence, and pending approvals." },
    pending: { zh: "待办审批", en: "Pending" },
    pendingHint: { zh: "审批等待你的上下文提案与技能候选。", en: "Approve context proposals and skill candidates waiting on you." },
    ops: { zh: "运营摘要", en: "Operations summary" },
    opsHint: { zh: "治理、交付、上下文、质量与集成信号计数。", en: "Review governance, delivery, context, quality, and integration signals." },
    assets: { zh: "资产", en: "Assets" },
    assetsHint: { zh: "浏览归一化的项目资产。", en: "Browse normalized project assets." },
    skills: { zh: "技能", en: "Skills" },
    skillsHint: { zh: "查看内置与项目技能。", en: "Inspect built-in and project skills." },
    knowledge: { zh: "知识", en: "Knowledge" },
    knowledgeHint: { zh: "项目积累的团队知识。", en: "See the team knowledge accumulated in this project." },
    context: { zh: "上下文", en: "Context" },
    contextHint: { zh: "检查已上传的上下文状态。", en: "Inspect uploaded context state." },
    security: { zh: "安全审计", en: "Security audit" },
    securityHint: { zh: "敏感治理审批、拒绝与主体。", en: "Inspect sensitive governance approvals, denials, and actors." },
    writebacks: { zh: "写回草稿", en: "Writebacks" },
    writebacksHint: { zh: "审阅 AI 生成的知识草稿。", en: "Review generated knowledge drafts." },
    agent: { zh: "Agent", en: "Agent" },
    intent: { zh: "意图", en: "Intent" },
    workItem: { zh: "工作项", en: "Work item" },
    started: { zh: "开始时间", en: "Started" },
    noWorkItem: { zh: "无工作项", en: "No work item" },
  },
};
