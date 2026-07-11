"use client";

import { useState } from "react";
import { updateScheduleSettings, type ScheduleSettings } from "../lib/api";

export default function ScheduleSettingsPanel({ initialSettings }: { initialSettings: ScheduleSettings }) {
  const [settings, setSettings] = useState(initialSettings);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  async function save() {
    setSaving(true);
    setSaved(false);
    setError("");
    try {
      const next = await updateScheduleSettings({ enabled: settings.enabled, run_time: settings.run_time, timezone: settings.timezone });
      setSettings(next);
      setSaved(true);
    } catch {
      setError("保存失败，请检查 API 服务状态。");
    } finally {
      setSaving(false);
    }
  }

  return <section className="schedulePanel"><div className="scheduleHeader"><div><span className="sectionLabel">AUTOMATION</span><h2>每日自动运行</h2><p>按设定时间自动完成检索、分析和 Changes 生成。</p></div><label className="switchLabel"><input type="checkbox" checked={settings.enabled} onChange={(event) => setSettings({ ...settings, enabled: event.target.checked })} /><span className="switchTrack" /><b>{settings.enabled ? "已开启" : "已关闭"}</b></label></div><div className="scheduleFields"><label><span>运行时间</span><input type="time" value={settings.run_time} onChange={(event) => setSettings({ ...settings, run_time: event.target.value })} /></label><label><span>时区</span><select value={settings.timezone} onChange={(event) => setSettings({ ...settings, timezone: event.target.value })}><option value="Asia/Tokyo">日本标准时间 · Asia/Tokyo</option><option value="Asia/Shanghai">中国标准时间 · Asia/Shanghai</option><option value="UTC">协调世界时 · UTC</option><option value="America/Los_Angeles">太平洋时间 · America/Los_Angeles</option></select></label><button className="saveScheduleButton" onClick={save} disabled={saving}>{saving ? "保存中..." : "保存设置"}</button></div><div className="scheduleFooter"><span>{settings.last_run_date ? `上次自动运行：${settings.last_run_date}` : "尚未自动运行"}</span>{saved && <strong>设置已保存</strong>}{error && <strong className="scheduleError">{error}</strong>}</div></section>;
}
