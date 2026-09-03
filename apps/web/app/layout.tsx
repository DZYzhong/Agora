import type { ReactNode } from "react";
import { headers } from "next/headers";
import { Sidebar } from "../components/Sidebar";
import { currentLang } from "../lib/i18n";
import "./theme.css";

export const metadata = {
  title: "Agora",
  description: "Team AI Project Harness",
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const lang = await currentLang();
  let pathname = "";
  try {
    const headerStore = await headers();
    pathname = headerStore.get("x-pathname") ?? "";
  } catch {
    pathname = "";
  }
  const standalone =
    pathname === "/login" ||
    pathname.startsWith("/login") ||
    pathname.startsWith("/reauth");

  return (
    <html lang={lang}>
      <body className="min-h-screen bg-canvas">
        {standalone ? (
          <>{children}</>
        ) : (
          <div className="flex min-h-screen">
            <Sidebar />
            <div className="min-w-0 flex-1">{children}</div>
          </div>
        )}
      </body>
    </html>
  );
}
