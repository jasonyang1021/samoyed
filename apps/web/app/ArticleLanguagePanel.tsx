"use client";

import { useState } from "react";

type Translation = { locale: string; provider: string; title: string; content: string; summary: string; facts: string[] };
export default function ArticleLanguagePanel({ changeId, sourceTitle, sourceContent, sourceSummary, sourceFacts, sourceType, date, author, source, url, labImpact, aiGenerated }: { changeId: string; sourceTitle: string; sourceContent: string; sourceSummary: string; sourceFacts: string[]; sourceType: string; date: string; author: string; source: string; url?: string | null; labImpact: boolean; aiGenerated: boolean }) {
  const [locale, setLocale] = useState("en");
  const [value, setValue] = useState<Translation>({ locale: "en", provider: "source", title: sourceTitle, content: sourceContent, summary: sourceSummary, facts: sourceFacts });
  const [loading, setLoading] = useState(false);
  async function changeLocale(next: string) {
    setLocale(next);
    if (next === "en") { setValue({ locale: "en", provider: "source", title: sourceTitle, content: sourceContent, summary: sourceSummary, facts: sourceFacts }); return; }
    setLoading(true);
    try { const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL ?? ""}/api/translations/${changeId}?locale=${next}`, { credentials: "include" }); const translated = await response.json(); setValue(translated); } finally { setLoading(false); }
  }
  return <article className="rawArticle"><div className="rawArticleMeta"><span>{sourceType}</span><span>{date}</span><label className="articleLanguage"><span>文章语言</span><select value={locale} onChange={(event) => changeLocale(event.target.value)}><option value="en">English</option><option value="zh">中文</option><option value="ja">日本語</option></select></label>{loading && <span className="translationLoading">AI 翻译中...</span>}</div><h2>{value.title}</h2><div className="rawContent" data-no-translate>{value.content || "来源未提供正文内容。"}</div><div className="rawArticleFooter"><span>作者：{author}</span><span>来源：{source}</span>{url && <a className="sourceLink" href={url} target="_blank" rel="noreferrer">打开原文 ↗</a>}</div><div className="processingFlow"><span className="flowTitle">处理流程</span><span className="flowStep complete">01 来源采集</span><span className="flowLine" /><span className="flowStep complete">02 去重</span><span className="flowLine" /><span className="flowStep complete">03 相关性判断</span><span className="flowLine" /><span className={`flowStep ${aiGenerated ? "complete" : "pending"}`}>04 {aiGenerated ? "AI 判断" : "Radar 判断"}</span><span className="flowLine" /><span className={`flowStep ${labImpact ? "complete" : "pending"}`}>05 Lab 参考</span></div></article>;
}
