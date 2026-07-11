"use client";

import { useState } from "react";
import { addLabWatchItem, removeLabWatchItem, type WatchItem } from "../../../lib/api";

const labels = { company: "企业", university: "高校", professor: "教授", topic: "主题", conference: "会议" } as const;

export default function LabSettingsPanel({ labId, initialItems }: { labId: string; initialItems: WatchItem[] }) {
  const [items, setItems] = useState(initialItems);
  const [kind, setKind] = useState<keyof typeof labels>("company");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  async function addItem(event: React.FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    setSaving(true); setMessage("");
    try {
      const item = await addLabWatchItem(labId, { kind, name: name.trim(), description: description.trim() || null });
      setItems((current) => current.some((existing) => existing.id === item.id) ? current : [...current, item]);
      setName(""); setDescription(""); setMessage("关注对象已保存。");
    } catch { setMessage("保存失败，请确认你是这个 Lab 的管理员。"); }
    finally { setSaving(false); }
  }

  async function removeItem(item: WatchItem) {
    try { await removeLabWatchItem(labId, item.id); setItems((current) => current.filter((existing) => existing.id !== item.id)); } catch { setMessage("删除失败，请稍后再试。"); }
  }

  return <section className="labSettingsPanel"><div className="settingsFormHeader"><div><span className="sectionLabel">WATCH CONFIGURATION</span><h2>关注对象</h2><p className="muted">这些对象会影响本 Lab 的检索范围和相关性判断。</p></div></div><form className="labWatchForm" onSubmit={addItem}><select value={kind} onChange={(event) => setKind(event.target.value as keyof typeof labels)}>{Object.entries(labels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><input value={name} onChange={(event) => setName(event.target.value)} placeholder="名称，例如：Intel、张教授" /><input value={description} onChange={(event) => setDescription(event.target.value)} placeholder="关注理由（可选）" /><button type="submit" disabled={saving}>{saving ? "保存中" : "添加关注"}</button></form>{message && <p className="settingsMessage">{message}</p>}<div className="labWatchGrid">{items.map((item) => <div className="labWatchChip" key={item.id}><span><b>{item.name}</b><small>{labels[item.kind as keyof typeof labels] || item.kind}</small></span><button type="button" aria-label={`删除${item.name}`} onClick={() => removeItem(item)}>×</button></div>)}</div></section>;
}
