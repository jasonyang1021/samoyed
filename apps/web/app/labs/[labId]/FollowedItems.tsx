"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getLabWatchArticles, type WatchArticle, type WatchItem } from "../../lib/api";

const kindLabels: Record<string, string> = { company: "企业", university: "高校", professor: "教授", topic: "主题", conference: "学术会议" };

export default function FollowedItems({ initialItems, labId }: { initialItems: WatchItem[]; labId: string }) {
  const items = initialItems.filter((item) => item.is_following);
  const [selected, setSelected] = useState<WatchItem | null>(null);
  const [articles, setArticles] = useState<WatchArticle[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!selected) return;
    setLoading(true); setArticles([]);
    getLabWatchArticles(labId, selected.id).then(setArticles).catch(() => setArticles([])).finally(() => setLoading(false));
  }, [labId, selected]);

  return <><section className="followStrip followStripInteractive"><span className="sectionLabel">正在关注</span>{items.map((item) => <button className="tag followTag" key={item.id} type="button" onClick={() => setSelected(item)}>{item.name}</button>)}<Link className="insightReportLink" href={`/labs/${encodeURIComponent(decodeURIComponent(labId))}/report`} target="_blank">AI 洞察报告 <span>↗</span></Link></section>{selected && <div className="followInfoBackdrop" role="presentation" onClick={() => setSelected(null)}><section className="followInfoDialog followSearchDialog" role="dialog" aria-modal="true" aria-labelledby="follow-info-title" onClick={(event) => event.stopPropagation()}><div className="modalHeader"><div><span className="sectionLabel">MY LAB / SEARCH</span><h2 id="follow-info-title">{selected.name}</h2></div><button className="modalClose" aria-label="关闭" onClick={() => setSelected(null)}>×</button></div><span className="followInfoType">{kindLabels[selected.kind] || selected.kind}</span><p>{selected.description || "正在从当前 Lab 的论文、新闻、会议和公开资料中查找相关信息。"}</p>{loading ? <div className="followSearchLoading">正在检索相关资料…</div> : articles.length ? <div className="followArticleGrid">{articles.map((article) => <article className="followArticleCard" key={article.id}>{article.image_url && <img src={article.image_url} alt="" /> }<div><span>{article.source_title}</span><h3>{article.title}</h3><p>{article.summary}</p><a href={article.url} target="_blank" rel="noreferrer">查看原文 ↗</a></div></article>)}</div> : <div className="followSearchEmpty">暂时没有检索到相关资料，请先运行一次雷达。</div>}</section></div>}</>;
}
