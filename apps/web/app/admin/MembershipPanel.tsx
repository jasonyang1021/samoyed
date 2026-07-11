"use client";

import { useState } from "react";
import { updateMembership, type LabMembership } from "../lib/api";

const labels = { lab_admin: "Lab 管理员", lab_user: "Lab 用户" } as const;

export default function MembershipPanel({ initialMemberships }: { initialMemberships: LabMembership[] }) {
  const [memberships, setMemberships] = useState(initialMemberships);
  const [saving, setSaving] = useState("");
  const [error, setError] = useState("");

  async function changeRole(membership: LabMembership, role: LabMembership["role"]) {
    setSaving(`${membership.user_id}:${membership.lab_id}`);
    setError("");
    try {
      const updated = await updateMembership(membership.user_id, membership.lab_id, role);
      setMemberships((current) => current.map((item) => item.user_id === updated.user_id && item.lab_id === updated.lab_id ? updated : item));
    } catch {
      setError("角色保存失败，请检查 API 服务状态。");
    } finally {
      setSaving("");
    }
  }

  return <section className="membershipPanel"><div className="sectionHeading"><div><span className="sectionLabel">ACCESS</span><h2>Lab 成员权限</h2><p className="muted">用户首次登录后会出现在这里，再为其分配 Lab 角色。</p></div></div>{memberships.length === 0 ? <div className="emptyFeed">还没有 Lab 成员。用户完成 Google 登录后会自动出现。</div> : <div className="membershipList">{memberships.map((membership) => { const key = `${membership.user_id}:${membership.lab_id}`; return <div className="membershipRow" key={key}><div><strong>{membership.name || membership.email}</strong><small>{membership.email} · {membership.lab_name}</small></div><select value={membership.role} disabled={saving === key} onChange={(event) => changeRole(membership, event.target.value as LabMembership["role"])}>{Object.entries(labels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div>; })}</div>}{error && <p className="radarError">{error}</p>}</section>;
}
