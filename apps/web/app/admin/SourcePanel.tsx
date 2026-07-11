import type { SourceRecord } from "../lib/api";

function formatDate(value: string | null) { return value ? new Intl.DateTimeFormat("zh-CN", { month: "short", day: "numeric", year: "numeric" }).format(new Date(value)) : "暂无"; }

export default function SourcePanel({ sources }: { sources: SourceRecord[] }) {
  return <section className="sourceAdminPanel"><div className="sectionHeading"><div><span className="sectionLabel">DATA SOURCES</span><h2>数据来源</h2><p className="muted">这里展示系统实际配置的新闻、论文、会议、专利和 AI 检索来源。</p></div><span className="updateCount">{sources.length} 个来源</span></div><div className="sourceAdminList">{sources.map((source) => <article className="sourceAdminRow" key={source.id}><div className="sourceAdminMain"><strong>{source.title}</strong><small>{source.source_type} · {source.format || "未配置格式"}</small>{source.url && <a href={source.url} target="_blank" rel="noreferrer">查看来源地址 ↗</a>}</div><div className="sourceAdminMetric"><strong>{source.document_count}</strong><small>篇资料</small></div><div className="sourceAdminDates"><span>最新发布：{formatDate(source.latest_published_at)}</span><span>最近抓取：{formatDate(source.latest_fetched_at)}</span></div><span className={`sourceState ${source.status === "有数据" ? "ready" : "pending"}`}>{source.status}</span></article>)}</div></section>;
}
