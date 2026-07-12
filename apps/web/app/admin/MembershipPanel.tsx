"use client";

import { useState } from "react";
import { updateLabMembership, updateMembership, type LabMembership } from "../lib/api";

const labels = { lab_admin: "Lab 管理员", lab_user: "Lab 用户" } as const;

export default function MembershipPanel({ initialMemberships, labId }: { initialMemberships: LabMembership[]; labId?: string }) {
  const [memberships, setMemberships] = useState(labId ? initialMemberships.filter((item) => item.lab_id === labId) : initialMemberships);
  const [saving, setSaving] = useState("");
  const [error, setError] = useState("");
  const groupedMemberships = memberships.reduce<Array<{ userId: string; email: string; name: string | null; labs: LabMembership[] }>>((groups, membership) => {
    const existing = groups.find((group) => group.userId === membership.user_id);
    if (existing) {
      existing.labs.push(membership);
      return groups;
    }
    groups.push({ userId: membership.user_id, email: membership.email, name: membership.name, labs: [membership] });
    return groups;
  }, []).map((group) => ({ ...group, labs: [...group.labs].sort((a, b) => a.lab_name.localeCompare(b.lab_name)) }));

  async function changeRole(membership: LabMembership, role: LabMembership["role"]) {
    setSaving(`${membership.user_id}:${membership.lab_id}`);
    setError("");
    try {
      const updated = labId ? await updateLabMembership(labId, membership.user_id, role) : await updateMembership(membership.user_id, membership.lab_id, role);
      setMemberships((current) => current.map((item) => item.user_id === updated.user_id && item.lab_id === updated.lab_id ? updated : item));
    } catch {
      setError("角色保存失败，请检查 API 服务状态。");
    } finally {
      setSaving("");
    }
  }

  return <section className="membershipPanel"><div className="sectionHeading"><div><span className="sectionLabel">ACCESS</span><h2>Lab 成员权限</h2><p className="muted">{labId ? "管理这个 Lab 的成员和角色。只有系统管理员与本 Lab 管理员可操作。" : "成员权限已拆分到各个 Lab 管理页面。"}</p></div><span className="updateCount">{groupedMemberships.length} 位成员</span></div>{memberships.length === 0 ? <div className="emptyFeed">还没有 Lab 成员。用户完成 Google 登录后会自动出现。</div> : <div className="membershipTable"><div className="membershipTableHead"><span>成员</span><span>Lab 权限</span></div>{groupedMemberships.map((group) => <article className="membershipUserRow" key={group.userId}><div className="memberIdentity"><strong>{group.name || group.email}</strong><small>{group.email}</small></div><div className="memberLabGrid">{group.labs.map((membership) => { const key = `${membership.user_id}:${membership.lab_id}`; return <label className="memberLabRole" key={key}><span>{membership.lab_name}</span><select value={membership.role} disabled={saving === key} onChange={(event) => changeRole(membership, event.target.value as LabMembership["role"])}>{Object.entries(labels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>; })}</div></article>)}</div>}{error && <p className="radarError">{error}</p>}</section>;
}
