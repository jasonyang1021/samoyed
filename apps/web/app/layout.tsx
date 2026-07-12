import "./globals.css";
import type { ReactNode } from "react";
import AuthMenu from "./AuthMenu";
import LocaleRuntime from "./LocaleRuntime";
import { getCurrentUser } from "./lib/serverApi";

export const metadata = { title: "AI Research Radar", description: "AI-powered research change radar" };
export const dynamic = "force-dynamic";

export default async function RootLayout({ children }: { children: ReactNode }) {
  const initialUser = await getCurrentUser();
  return (
    <html lang="zh-CN">
      <body>
        <nav className="nav">
          <a className="brand" href="/"><img className="brandMark" src="/brand/samoyed-avatar.png" alt="Samoyed" /><span className="brandCopy"><strong>Samoyed</strong><small>AI Research Radar</small></span></a>
        <AuthMenu initialUser={initialUser} />
        </nav>
        <main className="shell">{children}</main>
        <LocaleRuntime />
      </body>
    </html>
  );
}
