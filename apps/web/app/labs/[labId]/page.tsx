import { getLabWeekChanges, getLabMonthChanges } from "../../lib/api";
import FollowedItems from "./FollowedItems";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getCurrentUser, getLabWatchItems } from "../../lib/serverApi";
import SnowyAssistant from "./SnowyAssistant";

export const dynamic = "force-dynamic";

export default async function LabPage({ params }: { params: Promise<{ labId: string }> }) {
  const user = await getCurrentUser();
  if (!user.authenticated) redirect("/");
  const { labId } = await params;
  const [changes, monthChanges, watchItems] = await Promise.all([getLabWeekChanges(labId), getLabMonthChanges(labId), getLabWatchItems(labId)]);
  const labName = user.lab_names[user.lab_ids.indexOf(labId)] || "Example Lab";

  function changeTypeLabel(change: { title: string; watch_items: string[] }) {
    const items = change.watch_items.join(" ");
    if (/Intel|Samsung|Absolics|TSMC|Corning/.test(items)) return "企业动态";
    if (/东京大学|MIT|东北大学/.test(items)) return "高校论文";
    if (/专利|patent/i.test(change.title)) return "专利";
    if (/ECTC|IEDM/.test(items)) return "学术顶会";
    return "其他技术信息";
  }

  function publicationLabel(change: { published_at: string | null }) {
    if (!change.published_at) return null;
    return new Intl.DateTimeFormat("en-US", { month: "short", day: "2-digit", year: "numeric" }).format(new Date(change.published_at));
  }

  function changeList(items: typeof changes) {
    return <section className="labChangeList">{items.length ? items.map((change) => <article className="labChangeRow" key={change.id}><div className="labChangeContent"><div className="labChangeTitle"><span className="badge">{changeTypeLabel(change)}</span><span className="muted">{change.title}</span>{publicationLabel(change) && <span className="publicationDate">PUBLISHED · {publicationLabel(change)}</span>}<h3>{change.change_summary}</h3></div><div className="labChangeInsight"><div><strong>为什么相关</strong><p>{change.why_relevant}</p></div><div><strong>判断影响</strong><p>{change.impact}</p></div></div></div><Link className="labChangeArrow" href={`/changes/${change.id}?lab=${encodeURIComponent(labId)}`} aria-label={`查看${change.title}详情`}>→</Link></article>) : <div className="emptyFeed">暂无相关变化。</div>}</section>;
  }

  return (
    <>
      <section className="radarHero labHero"><div><div className="eyebrow">MY LAB · {labName.toUpperCase()}</div><h1>本周有哪些变化值得关注？</h1><p>系统从你关注的企业、教授和学术会议中筛选信号，只把与 {labName} 研究范围相关的变化放到这里。</p></div><div className="heroInsight"><strong>本周判断</strong><span>{changes.length ? `${labName} 本周有 ${changes.length} 条相关变化，下面会分别说明它为什么相关，以及对当前判断有什么影响。` : `${labName} 本周暂时没有新的相关变化，系统会继续观察企业、教授和学术会议的公开信号。`}</span></div></section>
      <FollowedItems initialItems={watchItems} labId={labId} />
      <div className="sectionHeading labHeading"><div><span className="sectionLabel">LAB INTERPRETATION · THIS WEEK</span><h2>本周新增</h2></div><span className="updateCount">{changes.length} 条</span></div>
      {changeList(changes)}
      <div className="sectionHeading labHeading weeklyLabHeading"><div><span className="sectionLabel">THIS MONTH</span><h2>本月新增</h2></div><span className="updateCount">{monthChanges.length} 条</span></div>
      {changeList(monthChanges)}
      <SnowyAssistant labId={labId} labName={labName} />
    </>
  );
}
