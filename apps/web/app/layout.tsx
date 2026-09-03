import type { ReactNode } from "react";
import { Nav } from "../components/Nav";
import { currentLang } from "../lib/i18n";
import "./theme.css";

export const metadata = {
  title: "Agora",
  description: "Team AI Project Harness",
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const lang = await currentLang();
  return (
    <html lang={lang}>
      <body>
        <Nav />
        {children}
      </body>
    </html>
  );
}
