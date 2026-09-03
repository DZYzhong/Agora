# Agora 治理界面 UI/UE 主流重设计方案（评审稿）

> 状态：**待用户评审**。评审通过后按批次实施（每批 tsc/build/pytest 绿 + 视觉走查）。
> 范围：`apps/web`（Next.js 15 App Router，全 Server Components，24 个页面）。
> 日期：2026-09-03

## 1. 现状评估（实测）

当前界面是一套"可用但未设计"的样式：单文件 `styles.css`（776 行）承载全部样式；全局只有一条 56px 顶栏（brand + Projects/Users + 登录态）；页面用 `.page > .panel/.grid` 平铺卡片；无侧边导航、无统一页面骨架、无组件状态样式体系。

具体问题（按影响排序）：

| # | 问题 | 位置举例 |
|---|---|---|
| P1 | 信息架构扁平：所有功能页都要从项目首页的 12 个入口卡片点进去，项目内没有常驻导航 | 项目首页 `.grid` 12 张卡片 |
| P2 | 无层级感：登录/列表/详情/审批长得都一样，用户不知道自己在哪、能做什么 | 全站 |
| P3 | 状态只有文字 + 少量彩色圆点，缺少语义化状态色/徽章，扫描效率低 | status/pending/skills 页 |
| P4 | 空态缺失：多数列表为空时只显示空表或 "0"，无引导 | assets/sessions/writebacks |
| P5 | 反馈弱：审批/操作成功无 toast/反馈；表单错误仅有内联红字 | approve 路由 redirect、login error |
| P6 | 细节粗糙：无 hover/active 态统一规范、时间戳原始 ISO 串、长文本无截断 | 各列表 |
| P7 | 品牌与辨识度弱：无 logo/图标体系，纯文字链接 | Nav |
| P8 | 可访问性/响应式未系统化：无 focus 环规范、窄屏无适配策略 | 全站 |

## 2. 设计目标与原则

1. **主流 SaaS 后台范式**：侧边栏主导航 + 顶栏（面包屑/搜索/用户菜单），参考 Linear / Vercel / GitHub / Stripe 的简洁现代风。
2. **简约大气**：浅色底、克制配色、大留白、清晰层级；一屏一主任务。
3. **易交互**：一切可点的都有 hover/active/focus 反馈；主操作按钮恒定在右上/右下；审批流最短路径。
4. **可扩展**：设计令牌（design tokens）+ 组件类，新页面零成本接入；**保持全 Server Components、零新运行时依赖**（技术路线论证见 §7）。
5. **信息设计优先**：治理类数据用"状态徽章 + 时间线 + 摘要卡片"呈现，扫一眼能决策。

## 3. 信息架构与导航

```
┌────────┬────────────────────────────────────────────┐
│ 侧边栏  │  顶栏: 当前项目 / 面包屑        [搜索] [用户] │
│        ├────────────────────────────────────────────┤
│ ▸ 全局  │                                            │
│  项目   │             页面内容区                      │
│  用户   │     （项目上下文时项目导航高亮/切换）          │
│  待我审批│                                            │
│        │                                            │
│ ────── │                                            │
│ 项目级  │                                            │
│  概览   │                                            │
│  工作项 │                                            │
│  待办审批│                                            │
│  会话   │                                            │
│  上下文 │                                            │
│  知识   │                                            │
│  资产   │                                            │
│  技能   │                                            │
│  状态/质量│                                            │
│  安全审计│                                            │
└────────┴────────────────────────────────────────────┘
```

- **全局导航**（无项目上下文时）：项目（工作台首页）、用户（管理）、待我审批（跨项目聚合）等。
- **项目级导航**：进入某项目后，侧边栏切换为项目导航（概览/工作项/待办/会话/上下文/知识/资产/技能/状态/写回/安全），顶栏显示项目名 + 面包屑；全局"所有项目"入口常驻底部。
- 未登录访问 `/projects` 仍走 middleware 登录门（现状保留）。

## 4. 设计令牌（浅色主题，草案值）

```css
:root {
  /* 品牌 */
  --color-brand: #2563eb;            /* primary 蓝 */
  --color-brand-hover: #1d4ed8;
  --color-brand-weak: #eff6ff;

  /* 中性 */
  --color-bg: #f8fafc;               /* 页面底 */
  --color-surface: #ffffff;          /* 卡片/面板 */
  --color-border: #e2e8f0;
  --color-text: #0f172a;
  --color-text-secondary: #64748b;
  --color-text-faint: #94a3b8;

  /* 语义状态 */
  --color-success: #16a34a;  --color-success-weak: #f0fdf4;
  --color-warning: #d97706;  --color-warning-weak: #fffbeb;
  --color-danger:  #dc2626;  --color-danger-weak:  #fef2f2;
  --color-info:    #0ea5e9;  --color-info-weak:    #f0f9ff;

  /* 字体：Inter / system-ui；数值 tabular-nums */
  /* 圆角：sm 6 / md 8 / lg 12 / full */
  /* 阴影：card 0 1px 2px rgba(15,23,42,.05) */
  /* 间距：4 的倍数（4/8/12/16/24/32/48） */
  /* 布局：侧栏 232px；内容 max-width 1180px；断点 960/1280 */
}
```

- 状态→色映射固定：`active/approved/accepted/completed/ready` = 绿；`pending/submitted/candidate/running` = 蓝或琥珀；`failed/rejected/denied/disabled/archived` = 红/灰。写入统一 badge 组件。

## 5. 组件规范（纯 CSS 类，全站统一）

- `app-shell`（侧栏+顶栏+内容）、`sidebar`、`topbar`、`breadcrumb`
- `badge status-*`、`card`、`table`（斑马/hover/列对齐）、`empty-state`（图标+文案+CTA）
- `btn btn-primary/secondary/ghost/danger`、`btn-sm`、`input/select/textarea`（focus 环统一）、`form-row`
- `kpi`（大数字卡）、`timeline`、`stepper`（复用现 B4 stepper 语义色）、`alert`
- 反馈：路由层操作成功用**服务端渲染的 flash 或页面内成功条**（server components 下不用 toast 库，用 URL 参数/`searchParams` 驱动轻量提示条，例如 `?ok=approved`）
- 徽章/状态点全站语义统一；所有时间戳用相对时间（x 分钟前）+ title 原值

## 6. 页面级改造对照（24 页分批）

| 批次 | 页面 | 改造要点 |
|---|---|---|
| B1 壳 | layout/Nav→侧边栏+顶栏；全局 404/错误/空态 | 新骨架替换顶栏 |
| B2 | 登录、reauth | 居中卡片式认证页、品牌区、错误提示条 |
| B3 | 项目列表、项目首页 | 列表→表格/卡片混合 + KPI；首页→项目概览（状态卡+待办摘要+最近活动），**移除初始化面板**（随 C1 一并清理） |
| B4 | 工作项列表/详情、sessions 列表/详情 | 详情页统一头部（标题+状态徽章+操作区）、stepper 语义化 |
| B5 | pending、skills、context、knowledge | 审批队列卡片化（申请者/时间/摘要/审阅 CTA） |
| B6 | assets、writebacks、security、operations、users | 表格规范+筛选+空态+详情抽屉/跳转 |

每批验收：`tsc --noEmit` + `next build` + pytest 相关用例 + 我逐页截图视觉走查（如可截图则附对比）。

## 7. 技术路线对比与推荐

| 路线 | 优点 | 缺点 | 结论 |
|---|---|---|---|
| **A. 纯 CSS 设计系统**（推荐） | 零新依赖；保持全 Server Components 与现有架构；构建不变、风险最低；可控 token | 类名需自维护 | ✅ 推荐 |
| B. Tailwind CSS v4 | 原子类快、生态主流 | 构建链改造（PostCSS 插件）、类名噪音、与本项目"不引大库"惯例冲突 | 次选 |
| C. shadcn/ui + Radix | 现成组件最全、最"主流" | 需大量页面改 client 组件，破坏现有 server-only + cookie/CSRF 直传模型，改造与回归成本最高 | ❌ 不推荐 |

**推荐 A**：本项目页面全是服务端组件、靠 `cookies()`/表单路由直传浏览器凭据——保持 server-only 是安全与架构红线；CSS 令牌+组件类足以达到主流观感（Linear/Vercel 级视觉靠的正是克制设计系统而非组件库）。若你坚持 Tailwind 也可，代价是构建与类名重构，评审时请一并拍板。

## 8. 需要你拍板的点

1. 技术路线：**A 纯 CSS（推荐）/ B Tailwind / C shadcn**？
2. 深浅色：**浅色（推荐，§4 草案）/ 深色 / 浅色为主+深色可选**？
3. 界面语言：当前 `lang="en"` 全英文——保持英文 / 中英切换 / 中文？
4. 导航范式：侧边栏方案（推荐）是否 OK，还是保持顶栏+增强？

## 9. 与在途工作的关系

- 页面改造与 **C1（移除项目首页初始化面板）** 同步进行，避免二次返工。
- 用户管理页（users）在 PR3（角色/成员管理）中会扩展，B6 先做视觉规范、功能结构留给 PR3。
