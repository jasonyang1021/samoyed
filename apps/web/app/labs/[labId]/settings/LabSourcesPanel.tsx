"use client";

import { useState } from "react";
import { updateLabSource, type LabSourceRecord } from "../../../lib/api";

function formatType(value: string) {
  const labels: Record<string, string> = { paper_feed: "论文订阅", paper_api: "论文 API", news_feed: "新闻订阅", company_news: "企业动态", company_product: "企业资料", conference_article: "会议资料", patent_feed: "专利动态", patent_api: "专利 API" };
  return labels[value] || value;
}

export default function LabSourcesPanel({ labId, initialSources }: { labId: string; initialSources: LabSourceRecord[] }) {
  const [sources, setSources] = useState(initialSources);
  const [working, setWorking] = useState<string | null>(null);
  const [message, setMessage] = useState("");

  async function toggle(source: LabSourceRecord) {
    if (!source.source_enabled) return;
    setWorking(source.source_id); setMessage("");
    try {
      const updated = await updateLabSource(labId, source.source_id, !source.enabled);
      setSources((current) => current.map((item) => item.source_id === updated.source_id ? updated : item));
    } catch { setMessage("来源状态更新失败，请稍后再试。"); }
    finally { setWorking(null); }
  }

  const recommended = sources.filter((source) => source.recommended && !source.enabled);
  return <section className="labSourcesPanel"><div className="settingsFormHeader"><div><span className="sectionLabel">SOURCE SELECTION</span><h2>数据来源</h2><p className="muted">系统管理员维护来源目录，你可以为本 Lab 选择需要使用的来源。</p></div><span className="sourceSelectionCount">已启用 {sources.filter((source) => source.enabled).length} / {sources.length}</span></div>{recommended.length > 0 && <div className="sourceRecommendationNote"><strong>发现 {recommended.length} 个推荐来源</strong><span>推荐结果根据本 Lab 的关注对象和研究方向生成，请确认后启用。</span></div>}{message && <p className="settingsMessage">{message}</p>}<div className="labSourceList">{sources.map((source) => <article className={`labSourceRow${source.enabled ? " selected" : ""}`} key={source.source_id}><div className="labSourceInfo"><div className="labSourceTitle"><strong>{source.title}</strong>{source.recommended && <span className="sourceRecommended">推荐</span>}</div><small>{formatType(source.source_type)} · {source.format || "未配置格式"} · {source.status}</small><p>{source.recommendation_reason}</p></div><button type="button" className={`sourceUseButton${source.enabled ? " active" : ""}`} disabled={!source.source_enabled || working === source.source_id} onClick={() => toggle(source)}>{!source.source_enabled ? "系统已停用" : source.enabled ? "已使用" : "使用此来源"}</button></article>)}</div>{sources.length === 0 && <div className="emptyFeed">系统管理员还没有配置可用的数据来源。</div>}</section>;
}
