import type { SourceRecord } from "../lib/api";
import Link from "next/link";

function formatDate(value: string | null) { return value ? new Intl.DateTimeFormat("zh-CN", { month: "short", day: "numeric", year: "numeric" }).format(new Date(value)) : "暂无"; }

export default function SourcePanel({ sources }: { sources: SourceRecord[] }) {
  const ready = sources.filter((source) => source.status === "有数据").length;
  const pending = sources.length - ready;
  return <section className="sourceAdminPanel sourceSummaryPanel"><div className="sectionHeading"><div><span className="sectionLabel">DATA SOURCES</span><h2>数据来源</h2><p className="muted">新闻、论文、会议、专利和 AI 检索来源的接入概览。</p></div><Link className="sourceManageButton" href="/admin/sources">管理数据来源 →</Link></div><div className="sourceSummaryStats"><div><strong>{sources.length}</strong><span>已配置来源</span></div><div><strong>{ready}</strong><span>当前有数据</span></div><div><strong>{pending}</strong><span>待配置或待抓取</span></div><div><strong>{sources.reduce((total, source) => total + source.document_count, 0)}</strong><span>已入库资料</span></div></div></section>;
}
