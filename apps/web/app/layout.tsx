import "./globals.css";
import Link from "next/link";
import type { ReactNode } from "react";

export const metadata = { title: "Research Radar", description: "Lab-centric research change radar" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <nav className="nav">
          <strong>Research Radar</strong>
          <Link href="/">今日变化</Link>
          <Link href="/research-pool">公共情报池</Link>
          <Link href="/labs/glass-core">Lab 空间</Link>
          <Link href="/admin">管理</Link>
        </nav>
        <main className="shell">{children}</main>
      </body>
    </html>
  );
}
