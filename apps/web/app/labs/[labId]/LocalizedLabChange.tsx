"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { LabChangeCard } from "../../lib/api";

type LocalizedValue = Pick<LabChangeCard, "title" | "change_summary" | "why_relevant" | "impact">;
type TranslationResponse = Partial<LocalizedValue> & { summary?: string };

function changeTypeLabel(change: LabChangeCard) {
  const items = change.watch_items.join(" ");
  if (/Intel|Samsung|Absolics|TSMC|Corning/.test(items)) return "企业动态";
  if (/东京大学|MIT|东北大学/.test(items)) return "高校论文";
  if (/专利|patent/i.test(change.title)) return "专利";
  if (/ECTC|IEDM/.test(items)) return "学术顶会";
  return "其他技术新闻";
}

function publicationLabel(change: LabChangeCard) {
  if (!change.published_at) return null;
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "2-digit", year: "numeric" }).format(new Date(change.published_at));
}

export default function LocalizedLabChange({ change, labId }: { change: LabChangeCard; labId: string }) {
  const original: LocalizedValue = { title: change.title, change_summary: change.change_summary, why_relevant: change.why_relevant, impact: change.impact };
  const [value, setValue] = useState<LocalizedValue>(original);
  const [locale, setLocale] = useState("zh-CN");

  useEffect(() => {
    setLocale(window.localStorage.getItem("radar-language") || document.documentElement.lang || "zh-CN");
  }, []);

  useEffect(() => {
    const target = locale === "ja" ? "ja" : locale === "en" ? "en" : "zh";
    if (target === "zh") {
      setValue(original);
      return;
    }

    let cancelled = false;
    fetch(`/api/translations/${encodeURIComponent(change.id)}?locale=${target}&lab_id=${encodeURIComponent(labId)}`, { credentials: "include" })
      .then((response) => response.ok ? response.json() : Promise.reject(new Error("translation failed")))
      .then((translated: TranslationResponse) => {
        if (!cancelled) setValue({ title: translated.title || original.title, change_summary: translated.summary || original.change_summary, why_relevant: translated.why_relevant || original.why_relevant, impact: translated.impact || original.impact });
      })
      .catch(() => { if (!cancelled) setValue(original); });
    return () => { cancelled = true; };
  // The source object is immutable for the lifetime of this server-rendered card.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locale, change.id, labId]);

  return <article className="labChangeRow"><div className="labChangeContent"><div className="labChangeTitle"><span className="badge">{changeTypeLabel(change)}</span><span className="muted">{value.title}</span>{publicationLabel(change) && <span className="publicationDate">PUBLISHED · {publicationLabel(change)}</span>}<h3>{value.change_summary}</h3></div><div className="labChangeInsight"><div><strong>为什么相关</strong><p>{value.why_relevant}</p></div><div><strong>判断影响</strong><p>{value.impact}</p></div></div></div><Link className="labChangeArrow" href={`/changes/${change.id}?lab=${encodeURIComponent(labId)}`} aria-label={`查看${value.title}详情`}>→</Link></article>;
}
