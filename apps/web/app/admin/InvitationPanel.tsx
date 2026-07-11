"use client";

import { useState } from "react";
import { createInvitation, type LabInvitation } from "../lib/api";

const roleLabels = { lab_admin: "Lab 管理员", lab_user: "Lab 用户" } as const;

export default function InvitationPanel({ initialInvitations }: { initialInvitations: LabInvitation[] }) {
  const [invitations, setInvitations] = useState(initialInvitations);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<LabInvitation["role"]>("lab_user");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  async function invite(event: React.FormEvent) {
    event.preventDefault();
    if (!email.trim()) return;
    setSaving(true); setMessage("");
    try {
      const item = await createInvitation({ email, lab_id: "lab-glass-core", role });
      setInvitations((current) => [item, ...current.filter((existing) => existing.id !== item.id)]);
      setEmail(""); setMessage("邀请已保存，用户下次登录后自动加入。");
    } catch { setMessage("邀请保存失败，请检查邮箱或 API 状态。"); }
    finally { setSaving(false); }
  }

  return <section className="invitePanel"><div className="sectionHeading"><div><span className="sectionLabel">INVITE</span><h2>邀请 Lab 成员</h2><p className="muted">填写 Google 邮箱，用户首次登录后自动获得权限。</p></div></div><form className="inviteForm" onSubmit={invite}><input type="email" placeholder="name@example.com" value={email} onChange={(event) => setEmail(event.target.value)} /><select value={role} onChange={(event) => setRole(event.target.value as LabInvitation["role"])}>{Object.entries(roleLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><button type="submit" disabled={saving}>{saving ? "保存中" : "保存邀请"}</button></form>{message && <p className="inviteMessage">{message}</p>}<div className="invitationList">{invitations.slice(0, 4).map((item) => <div className="invitationRow" key={item.id}><div><strong>{item.email}</strong><small>{item.lab_name} · {roleLabels[item.role]}</small></div><span className={`inviteStatus ${item.status}`}>{item.status === "accepted" ? "已加入" : "待登录"}</span></div>)}</div></section>;
}
