import Link from "next/link";
import { getTodayChanges, getWatchItems } from "../lib/api";

export const dynamic = "force-dynamic";
export default async function TopicsPage() {
  const [items, changes] = await Promise.all([getWatchItems(), getTodayChanges()]);
  const topics = items.filter((item) => item.kind === "topic");
  return <><div className="pageIntro"><span className="badge">TOPICS</span><h1>关注专题</h1><p className="muted">围绕一个问题，持续累积变化、资料和判断。</p></div><section className="topicGrid">{topics.map((topic) => { const related = changes.filter((change) => change.watch_items.includes(topic.id)); return <Link className="topicCard" id={topic.id} href="/labs/lab-glass-core" key={topic.id}><div className="topicKicker">专题 · {related.length} 条今日变化</div><h2>{topic.name}</h2><p>{topic.description}</p><span className="textLink">打开专题 →</span></Link>; })}</section><div className="sectionHeading compact"><div><span className="sectionLabel">RELATED FEED</span><h2>Glass Core 今日动态</h2></div></div><section className="feed">{changes.filter((change) => change.watch_items.includes("topic-glass-core")).map((change) => <Link className="feedItem" href={`/changes/${change.id}`} key={change.id}><div className="importance"><span>★★★★☆</span><small>{change.importance}级</small></div><div className="feedBody"><h3>{change.title}</h3><p>{change.change_summary}</p></div><span className="feedArrow">→</span></Link>)}</section></>;
}
