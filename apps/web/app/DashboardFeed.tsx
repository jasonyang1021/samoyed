"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { ChangeCard } from "./lib/api";

type Category = "all" | "company" | "university" | "patent" | "conference" | "technology";

const categoryMeta: Array<{ id: Category; label: string; note: string }> = [
  { id: "all", label: "全部变化", note: "所有来源" },
  { id: "company", label: "企业变化", note: "企业路线与量产" },
  { id: "university", label: "高校变化", note: "论文与研究" },
  { id: "patent", label: "专利变化", note: "专利与技术布局" },
  { id: "conference", label: "会议变化", note: "会议与议程" },
  { id: "technology", label: "技术变化", note: "技术状态迁移" },
];

function categoriesFor(change: ChangeCard): Array<Exclude<Category, "all">> {
  const categories: Array<Exclude<Category, "all">> = [];
  const items = change.watch_items.join(" ");
  if (/Intel|Samsung|Absolics|TSMC/.test(items)) categories.push("company");
  if (/东京大学|MIT/.test(items)) categories.push("university");
  if (/专利|patent/i.test(change.title)) categories.push("patent");
  if (/ECTC|IEDM/.test(items)) categories.push("conference");
  categories.push("technology");
  return categories;
}

export default function DashboardFeed({ changes }: { changes: ChangeCard[] }) {
  const [active, setActive] = useState<Category>("all");
  const counts = useMemo(() => changes.reduce<Record<string, number>>((result, change) => {
    for (const category of categoriesFor(change)) result[category] = (result[category] ?? 0) + 1;
    result.all = (result.all ?? 0) + 1;
    return result;
  }, {}), [changes]);
  const visibleChanges = active === "all" ? changes : changes.filter((change) => categoriesFor(change).includes(active));

  return <>
    <div className="sectionHeading dashboardHeading"><div><span className="sectionLabel">TODAY / {changes.length} UPDATES</span><h2>变化分类</h2></div><span className="refreshState"><span className="statusDot" /> UPDATED JUST NOW</span></div>
    <section className="categoryGrid">{categoryMeta.map((category) => <button className={`categoryCard ${active === category.id ? "active" : ""}`} key={category.id} onClick={() => setActive(category.id)}><span className="categoryLabel">{category.label}</span><strong>{counts[category.id] ?? 0}</strong><small>{category.note}</small></button>)}</section>
    <div className="updatesHeader"><div><span className="sectionLabel">UPDATES / {active === "all" ? "ALL SOURCES" : categoryMeta.find((item) => item.id === active)?.label}</span><h2>今日新增</h2></div><span className="updateCount">{visibleChanges.length} 条</span></div>
    <section className="feed">{visibleChanges.length === 0 ? <div className="emptyFeed">今天还没有这一类的新变化。</div> : visibleChanges.map((change) => <Link className="feedItem" href={`/changes/${change.id}`} key={change.id}><div className="importance"><span>{importanceStars[change.importance]}</span><small>{change.importance}级</small></div><div className="feedBody"><h3>{change.title}</h3><p>{change.change_summary}</p><div className="feedMeta">{change.watch_items.join(" · ")} <span>·</span> {change.affected_labs.join(" / ")}</div></div><span className="feedArrow">→</span></Link>)}</section>
  </>;
}

const importanceStars: Record<string, string> = { S: "★★★★★", A: "★★★★☆", B: "★★★☆☆", C: "★★☆☆☆" };
