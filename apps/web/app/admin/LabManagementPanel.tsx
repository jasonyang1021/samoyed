"use client";

import { useState } from "react";
import { createLab, deleteLab, type Lab, updateLab } from "../lib/api";
import Link from "next/link";

export default function LabManagementPanel({ initialLabs }: { initialLabs: Lab[] }) {
  const [labs, setLabs] = useState(initialLabs);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);

  async function addLab(event: React.FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    setSaving(true); setMessage("");
    try { const lab = await createLab({ name: name.trim(), description: description.trim() }); setLabs((current) => [...current, lab].sort((a, b) => a.name.localeCompare(b.name))); setName(""); setDescription(""); setMessage("Lab 已添加。"); } catch { setMessage("添加失败，名称可能已存在。"); }
    finally { setSaving(false); }
  }

  async function removeLab(lab: Lab) {
    if (!window.confirm(`确定删除 ${lab.name} 吗？相关成员关系和 Lab 判断也会删除。`)) return;
    try { await deleteLab(lab.id); setLabs((current) => current.filter((item) => item.id !== lab.id)); setMessage(`${lab.name} 已删除。`); } catch { setMessage("删除失败，请稍后再试。"); }
  }

  async function saveEdit(lab: Lab, form: HTMLFormElement) {
    const values = new FormData(form);
    setSaving(true); setMessage("");
    try { const updated = await updateLab(lab.id, { name: String(values.get("name") || ""), description: String(values.get("description") || "") }); setLabs((current) => current.map((item) => item.id === updated.id ? updated : item)); setEditing(null); setMessage("Lab 信息已更新。"); } catch { setMessage("编辑失败，请检查名称是否为空。"); } finally { setSaving(false); }
  }

  return <section className="labAdminPanel"><div className="sectionHeading"><div><span className="sectionLabel">LAB DIRECTORY</span><h2>Lab 管理</h2><p className="muted">点击 Lab 名称进入管理页，也可以编辑定位或删除 Lab。</p></div></div><form className="labAdminForm" onSubmit={addLab}><input value={name} onChange={(event) => setName(event.target.value)} placeholder="Lab 名称" /><input value={description} onChange={(event) => setDescription(event.target.value)} placeholder="一句话研究定位" /><button type="submit" disabled={saving}>{saving ? "保存中" : "添加 Lab"}</button></form>{message && <p className="settingsMessage">{message}</p>}<div className="labDirectory">{labs.map((lab) => editing === lab.id ? <form className="labDirectoryEdit" key={lab.id} onSubmit={(event) => { event.preventDefault(); void saveEdit(lab, event.currentTarget); }}><input name="name" defaultValue={lab.name} /><input name="description" defaultValue={lab.description || ""} /><div><button type="submit" disabled={saving}>保存</button><button type="button" onClick={() => setEditing(null)}>取消</button></div></form> : <div className="labDirectoryRow" key={lab.id}><div><Link href={`/labs/${lab.id}/settings`}><strong>{lab.name}</strong></Link><small>{lab.description || "尚未填写研究定位"}</small></div><div className="labDirectoryActions"><Link href={`/labs/${lab.id}/settings`}>管理</Link><button type="button" onClick={() => setEditing(lab.id)}>编辑</button><button type="button" onClick={() => removeLab(lab)}>删除</button></div></div>)}</div></section>;
}
