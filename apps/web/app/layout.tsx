import type { ReactNode } from "react";
import { Nav } from "../components/Nav";
import "./styles.css";

export const metadata = {
  title: "Agora",
  description: "Team AI Project Harness",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Nav />
        {children}
      </body>
    </html>
  );
}
