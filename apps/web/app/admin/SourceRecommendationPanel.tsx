"use client";

import { useMemo, useState } from "react";
import { addLabSources, getAdminSourceRecommendations, type SourceRecommendation } from "../lib/api";

function formatType(value: string) {
  const labels: Record<string, string> = { paper_feed: "论文订阅", paper_api: "论文 API", news_feed: "新闻订阅", company_news: "企业动态", company_product: "企业资料", conference_article: "会议资料", patent_feed: "专利动态", patent_api: "专利 API" };
  return labels[value] || value;
}

const BATCH_SIZE = 9;

export default function SourceRecommendationPanel() {
  const [items, setItems] = useState<SourceRecommendation[]>([]);
  const [activeLabId, setActiveLabId] = useState<string | null>(null);
  const [batchStart, setBatchStart] = useState(0);
  const [selected, setSelected] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");

  const labs = useMemo(() => Array.from(new Map(items.map((item) => [item.lab_id, item.lab_name])).entries()), [items]);
  const activeLabItems = items.filter((item) => item.lab_id === activeLabId && !item.enabled);
  const visibleItems = activeLabItems.length ? Array.from({ length: Math.min(BATCH_SIZE, activeLabItems.length) }, (_, index) => activeLabItems[(batchStart + index) % activeLabItems.length]) : [];

  async function recommend() {
    setLoading(true); setMessage("");
    try {
      const result = await getAdminSourceRecommendations();
      setItems(result); setActiveLabId(result[0]?.lab_id || null); setBatchStart(0); setSelected([]); setOpen(true);
    } catch { setMessage("推荐生成失败，请确认当前账号具有系统管理员权限。请稍后重试。"); }
    finally { setLoading(false); }
  }

  function switchLab(labId: string) {
    setActiveLabId(labId); setBatchStart(0); setSelected([]); setMessage("");
  }

  function nextBatch() {
    if (!activeLabItems.length) return;
    setBatchStart((current) => (current + BATCH_SIZE) % activeLabItems.length);
    setSelected([]); setMessage("");
  }

  function toggleSelected(source: SourceRecommendation) {
    if (source.enabled) return;
    setSelected((current) => current.includes(source.source_id) ? current.filter((id) => id !== source.source_id) : [...current, source.source_id]);
  }

  async function addSelected() {
    if (!activeLabId || selected.length === 0) return;
    setSaving(true); setMessage("");
    try {
      await addLabSources(activeLabId, selected);
      setItems((current) => current.map((item) => item.lab_id === activeLabId && selected.includes(item.source_id) ? { ...item, enabled: true } : item));
      setSelected([]); setMessage(`已成功加入 ${selected.length} 条来源。`);
    } catch { setMessage("批量加入失败，请稍后重试。"); }
    finally { setSaving(false); }
  }

  const canRotate = activeLabItems.length > BATCH_SIZE;
  return <div className="sourceRecommendationControls"><button className="sourceRecommendHeaderButton" type="button" onClick={recommend} disabled={loading}>{loading ? "分析中..." : "生成推荐"}</button>{message && <p className="settingsMessage sourceRecommendationMessage">{message}</p>}{open && <div className="sourceRecommendationBackdrop" role="presentation" onClick={() => setOpen(false)}><section className="sourceRecommendationDialog" role="dialog" aria-modal="true" aria-labelledby="source-recommendation-title" onClick={(event) => event.stopPropagation()}><header className="sourceRecommendationDialogHeader"><div><span className="sectionLabel">SOURCE DISCOVERY</span><h2 id="source-recommendation-title">为 Lab 选择数据来源</h2><p>每批展示 {BATCH_SIZE} 条推荐，选择后可以一次性加入当前 Lab。</p></div><div className="sourceRecommendationHeaderActions"><button type="button" className="sourceBatchButton" onClick={nextBatch} disabled={!canRotate} title={canRotate ? "查看下一批候选来源" : "当前可选候选不足一批"}>换一批</button><button type="button" className="modalClose" onClick={() => setOpen(false)} aria-label="关闭">×</button></div></header><div className="sourceRecommendationTabs" role="tablist">{labs.map(([labId, labName]) => <button type="button" role="tab" aria-selected={labId === activeLabId} className={labId === activeLabId ? "active" : ""} key={labId} onClick={() => switchLab(labId)}>{labName}<small>{items.filter((item) => item.lab_id === labId && !item.enabled).length} 条可选</small></button>)}</div>{activeLabItems.length === 0 ? <div className="emptySourceRecommendation">当前 Lab 已加入本批推荐来源，点击“生成推荐”可重新获取候选来源。</div> : <><div className="sourceRecommendationBatchHint">当前显示 {Math.min(BATCH_SIZE, activeLabItems.length)} 条，共 {activeLabItems.length} 条可选{canRotate ? "，可换一批" : "，已是全部候选"}。</div><div className="sourceRecommendationDialogGrid">{visibleItems.map((item) => { const checked = selected.includes(item.source_id); return <label className={`sourceRecommendationDialogCard${checked ? " checked" : ""}`} key={`${item.lab_id}-${item.source_id}`}><input type="checkbox" checked={checked} onChange={() => toggleSelected(item)} /><div><div className="sourceRecommendationCardTop"><strong>{item.title}</strong><span>{Math.round(item.score * 100)}%</span></div><small>{formatType(item.source_type)}{item.requires_api_key ? " · 需要 API Key" : ""}{item.source_enabled ? " · 可加入" : " · 选择后启用"}</small><p>{item.reason}</p></div></label>; })}</div></>}{message && <p className="settingsMessage">{message}</p>}<footer className="sourceRecommendationDialogFooter"><span>推荐来源仍由系统管理员统一维护，Lab 只选择使用范围。</span><button type="button" className="sourceRecommendButton" disabled={saving || selected.length === 0} onClick={addSelected}>{saving ? "加入中..." : `加入 ${selected.length} 条来源`}</button></footer></section></div>}</div>;
}
