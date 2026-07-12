"use client";

import { useState } from "react";
import Link from "next/link";
import type { WatchItem } from "../../lib/api";

const kindLabels: Record<string, string> = { company: "企业", university: "高校", professor: "教授", topic: "主题", conference: "学术会议" };

export default function FollowedItems({ initialItems, labId }: { initialItems: WatchItem[]; labId: string }) {
  const items = initialItems.filter((item) => item.is_following);
  const [selected, setSelected] = useState<WatchItem | null>(null);
  return <><section className="followStrip followStripInteractive"><span className="sectionLabel">正在关注</span>{items.map((item) => <button className="tag followTag" key={item.id} type="button" onClick={() => setSelected(item)}>{item.name}</button>)}<Link className="insightReportLink" href={`/labs/${encodeURIComponent(decodeURIComponent(labId))}/report`} target="_blank">AI 洞察报告 <span>↗</span></Link></section>{selected && <div className="followInfoBackdrop" role="presentation" onClick={() => setSelected(null)}><section className="followInfoDialog" role="dialog" aria-modal="true" aria-labelledby="follow-info-title" onClick={(event) => event.stopPropagation()}><div className="modalHeader"><div><span className="sectionLabel">MY LAB / FOLLOWING</span><h2 id="follow-info-title">{selected.name}</h2></div><button className="modalClose" aria-label="关闭" onClick={() => setSelected(null)}>×</button></div><span className="followInfoType">{kindLabels[selected.kind] || selected.kind}</span><p>{selected.description || "这个关注对象暂时还没有简介。后续检索会从相关新闻、论文、会议和公开资料中寻找相关变化。"}</p><div className="followInfoNote">相关变化会根据这个关注对象与当前 Lab 的研究范围进行筛选。</div></section></div>}</>;
}
