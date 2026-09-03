import type { Lang } from "./i18n";

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

export function relativeTime(iso: string | null | undefined, lang: Lang): string {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return iso;
  const diff = Date.now() - then;
  const abs = Math.abs(diff);
  const unit = (value: number, zh: string, en: string) =>
    lang === "zh"
      ? `${value} ${zh}${abs >= MINUTE ? "前" : ""}`
      : `${value} ${en} ago`;
  if (abs < MINUTE) return lang === "zh" ? "刚刚" : "just now";
  if (abs < HOUR) return unit(Math.floor(abs / MINUTE), "分钟", "min");
  if (abs < DAY) return unit(Math.floor(abs / HOUR), "小时", "h");
  if (abs < 30 * DAY) return unit(Math.floor(abs / DAY), "天", "d");
  return new Date(iso).toLocaleDateString(lang === "zh" ? "zh-CN" : "en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}
