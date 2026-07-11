"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import type { ChangeCard } from "./lib/api";

type Category = "company" | "university" | "patent" | "conference" | "technology";

const categoryMeta: Array<{ id: Category; label: string; note: string }> = [
  { id: "company", label: "新增企业新闻", note: "企业路线与量产" },
  { id: "university", label: "新增高校论文", note: "论文与研究" },
  { id: "patent", label: "新增专利", note: "专利与技术布局" },
  { id: "conference", label: "新增学术顶会", note: "会议与议程" },
  { id: "technology", label: "其他技术信息", note: "技术状态迁移" },
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

const entityNames: Record<Exclude<Category, "all">, string[]> = {
  company: ["Intel", "Samsung", "Absolics", "TSMC", "Corning"],
  university: ["东京大学", "MIT", "东北大学"],
  patent: [],
  conference: ["ECTC", "IEDM"],
  technology: [],
};

function displayEntities(change: ChangeCard, category: Category) {
  const knownNames = entityNames[category].filter((name) => change.watch_items.includes(name));
  if (knownNames.length) return knownNames.join(" · ");
  const focusedItems = change.watch_items.filter((item) => item !== "Glass Core");
  return focusedItems.length ? focusedItems.join(" · ") : "未识别具体对象";
}

function changeSummary(change: ChangeCard) {
  return change.change_summary?.trim() || "原文已收录，等待进一步分析。";
}

function publicationLabel(change: ChangeCard) {
  if (!change.published_at) return null;
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "2-digit", year: "numeric" }).format(new Date(change.published_at));
}

export default function DashboardFeed({ changes, weeklyChanges }: { changes: ChangeCard[]; weeklyChanges: ChangeCard[] }) {
  const [active, setActive] = useState<Category>("company");
  const [authenticated, setAuthenticated] = useState(false);
  useEffect(() => { fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL ?? ""}/api/auth/me`, { credentials: "include" }).then((response) => response.json()).then((value) => setAuthenticated(Boolean(value.authenticated))).catch(() => setAuthenticated(false)); }, []);
  const counts = useMemo(() => changes.reduce<Record<string, number>>((result, change) => {
    for (const category of categoriesFor(change)) result[category] = (result[category] ?? 0) + 1;
    return result;
  }, {}), [changes]);
  const visibleChanges = changes.filter((change) => categoriesFor(change).includes(active));
  const visibleWeeklyChanges = weeklyChanges.filter((change) => categoriesFor(change).includes(active));

  function renderChange(change: ChangeCard, guest = false) {
    const content = <div className="feedBody"><div className="labChangeTitle"><h3>{change.title}</h3>{!guest && publicationLabel(change) && <span className="publicationDate">PUBLISHED · {publicationLabel(change)}</span>}<p className="changeExcerpt">{changeSummary(change)}</p></div><div className="feedMeta"><strong>{displayEntities(change, active)}</strong>{change.affected_labs.length ? <><span> · </span>{change.affected_labs.join(" / ")}</> : null}</div></div>;
    return guest ? <article className="feedItem dashboardUpdateItem guestUpdate" key={change.id}>{content}<span className="feedLock">登录后查看</span></article> : <Link className="feedItem dashboardUpdateItem" href={`/changes/${change.id}`} key={change.id}>{content}<span className="feedArrow">→</span></Link>;
  }

  return <>
    <div className="sectionHeading dashboardHeading"><div><span className="sectionLabel">TODAY / {changes.length} UPDATES</span><h1 className="dashboardTitle">今日热点</h1></div><span className="refreshState"><span className="statusDot" /> UPDATED JUST NOW</span></div>
    <section className="categoryGrid">{categoryMeta.map((category) => <button className={`categoryCard ${active === category.id ? "active" : ""}`} key={category.id} onClick={() => setActive(category.id)}><span className="categoryLabel">{category.label}</span><strong>{counts[category.id] ?? 0}</strong><small>{category.note}</small></button>)}</section>
    <div className="updatesHeader"><div><span className="sectionLabel">UPDATES / {categoryMeta.find((item) => item.id === active)?.label}</span><h2>今日新增</h2></div><span className="updateCount">{visibleChanges.length} 条</span></div>
    <section className="feed">{visibleChanges.length === 0 ? <div className="emptyFeed">今天还没有这一类的新变化。</div> : visibleChanges.map((change) => renderChange(change, !authenticated))}</section>
    <div className="updatesHeader weeklyHeader"><div><span className="sectionLabel">THIS MONTH / {categoryMeta.find((item) => item.id === active)?.label}</span><h2>本月新增</h2></div><span className="updateCount">{visibleWeeklyChanges.length} 条</span></div>
    <section className="feed weeklyFeed">{visibleWeeklyChanges.length === 0 ? <div className="emptyFeed">本月暂无更早的相关变化。</div> : visibleWeeklyChanges.map((change) => renderChange(change, !authenticated))}</section>
  </>;
}
