"use client";

import type { LabAuditLog } from "../../../lib/api";

const labels: Record<string, string> = { membership_role_changed: "调整成员角色", invitation_created: "发出成员邀请" };

export default function AuditLogPanel({ entries }: { entries: LabAuditLog[] }) {
  return <section className="settingsPanel auditLogPanel"><div className="sectionHeading"><div><span className="sectionLabel">AUDIT LOG</span><h2>最近操作</h2><p className="muted">记录本 Lab 的权限和邀请变更。</p></div></div>{entries.length === 0 ? <div className="emptyFeed">还没有权限操作记录。</div> : <div className="auditLogList">{entries.map((entry) => <article key={entry.id}><div><strong>{labels[entry.action] || entry.action}</strong><span>{entry.target || "未指定对象"}</span></div><small>{entry.actor_name || entry.actor_email || "系统管理员"} · {new Intl.DateTimeFormat("zh-CN", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(entry.created_at))}</small></article>)}</div>}</section>;
}
