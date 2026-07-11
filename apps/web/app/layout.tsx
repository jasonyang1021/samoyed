import "./globals.css";
import type { ReactNode } from "react";
import AuthMenu from "./AuthMenu";
import LocaleRuntime from "./LocaleRuntime";

export const metadata = { title: "AI Research Radar", description: "AI-powered research change radar" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <nav className="nav">
          <a className="brand" href="/"><span className="brandMark">AI</span><strong>AI Research Radar</strong></a>
          <AuthMenu />
        </nav>
        <main className="shell">{children}</main>
        <LocaleRuntime />
      </body>
    </html>
  );
}
