import "./globals.css";
import Link from "next/link";
import type { ReactNode } from "react";

export const metadata = { title: "AI Research Radar", description: "AI-powered research change radar" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <nav className="nav">
          <Link className="brand" href="/"><span className="brandMark">AI</span><strong>AI Research Radar</strong></Link>
          <div className="topLinks"><Link href="/">Dashboard</Link><Link href="/labs/lab-glass-core">My Lab</Link></div>
        </nav>
        <main className="shell">{children}</main>
      </body>
    </html>
  );
}
