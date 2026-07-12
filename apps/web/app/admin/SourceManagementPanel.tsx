"use client";

import { useState } from "react";
import { deleteSource, runSource, setSourceEnabled, testSource, type SourceRecord } from "../lib/api";

function formatDate(value: string | null) { return value ? new Intl.DateTimeFormat("zh-CN", { month: "short", day: "numeric", year: "numeric" }).format(new Date(value)) : "暂无"; }

export default function SourceManagementPanel({ initialSources }: { initialSources: SourceRecord[] }) {
  const [sources, setSources] = useState(initialSources);
  const [selected, setSelected] = useState<SourceRecord | null>(null);
  const [message, setMessage] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [working, setWorking] = useState<string | null>(null);
  async function remove() {
    if (!selected) return;
    setDeleting(true); setMessage("");
    try { await deleteSource(selected.id); setSources((current) => current.filter((source) => source.id !== selected.id)); setSelected(null); setMessage("数据来源已删除，同时清理了该来源关联的资料和变化。"); } catch { setMessage("删除失败，请确认当前账号具有系统管理员权限。"); } finally { setDeleting(false); }
  }
  async function toggle(source: SourceRecord) {
    setWorking(source.id); setMessage("");
    try { const updated = await setSourceEnabled(source.id, !source.enabled); setSources((current) => current.map((item) => item.id === source.id ? updated : item)); } catch { setMessage("更新来源状态失败。"); } finally { setWorking(null); }
  }
  async function run(source: SourceRecord) {
    setWorking(source.id); setMessage("");
    try { const result = await runSource(source.id); setMessage(`${source.title}：抓取 ${result.fetched} 条，新增 ${result.created} 条。${result.error || ""}`); } catch { setMessage("来源抓取失败，请查看该来源的错误状态。"); } finally { setWorking(null); }
  }
  async function test(source: SourceRecord) {
    setWorking(source.id); setMessage("");
    try { const result = await testSource(source.id); setMessage(`${source.title}：${result.message}`); } catch { setMessage("来源测试失败。"); } finally { setWorking(null); }
  }
  return <><div className="sourceManagementList">{sources.map((source) => <article className="sourceManagementRow" key={source.id}><div className="sourceAdminMain"><strong>{source.title}</strong><small>{source.source_type} · {source.format || "未配置格式"}</small>{source.url && <a href={source.url} target="_blank" rel="noreferrer">查看来源地址 ↗</a>}{source.last_error && <small className="sourceError">最近错误：{source.last_error}</small>}</div><div className="sourceAdminMetric"><strong>{source.document_count}</strong><small>篇资料</small></div><div className="sourceAdminDates"><span>最新发布：{formatDate(source.latest_published_at)}</span><span>最近抓取：{formatDate(source.latest_fetched_at)}</span><span>健康检查：{formatDate(source.last_checked_at)}</span></div><span className={`sourceState ${source.status === "有数据" ? "ready" : source.status === "异常" ? "error" : "pending"}`}>{source.status}</span><div className="sourceActions"><button type="button" onClick={() => test(source)} disabled={working === source.id}>测试</button><button type="button" onClick={() => run(source)} disabled={working === source.id || !source.enabled}>立即抓取</button><button type="button" onClick={() => toggle(source)} disabled={working === source.id}>{source.enabled ? "停用" : "启用"}</button><button className="sourceDeleteButton" type="button" onClick={() => setSelected(source)}>删除</button></div></article>)}</div>{message && <p className="settingsMessage">{message}</p>}{selected && <div className="followInfoBackdrop" role="presentation" onClick={() => setSelected(null)}><section className="followInfoDialog sourceDeleteDialog" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}><div className="modalHeader"><div><span className="sectionLabel">REMOVE SOURCE</span><h2>删除数据来源？</h2></div><button className="modalClose" type="button" onClick={() => setSelected(null)}>×</button></div><p>将删除“{selected.title}”以及该来源已入库的资料、分析和变化记录。这个操作不可撤销。</p><div className="modalFooter"><button className="cancelButton" type="button" onClick={() => setSelected(null)}>取消</button><button className="saveFollowButton" type="button" disabled={deleting} onClick={remove}>{deleting ? "删除中..." : "确认删除"}</button></div></section></div>}</>;
}
