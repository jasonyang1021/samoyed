import { getLabWeekChanges, getLabMonthChanges } from "../../lib/serverApi";
import FollowedItems from "./FollowedItems";
import { redirect } from "next/navigation";
import { getCurrentUser, getLabWatchItems } from "../../lib/serverApi";
import SnowyAssistant from "./SnowyAssistant";
import LocalizedLabChange from "./LocalizedLabChange";

export const dynamic = "force-dynamic";

export default async function LabPage({ params }: { params: Promise<{ labId: string }> }) {
  const user = await getCurrentUser();
  if (!user.authenticated) redirect("/");
  const { labId: encodedLabId } = await params;
  const labId = decodeURIComponent(encodedLabId);
  const [changes, monthChanges, watchItems] = await Promise.all([getLabWeekChanges(labId), getLabMonthChanges(labId), getLabWatchItems(labId)]);
  const labName = user.lab_names[user.lab_ids.indexOf(labId)] || "Example Lab";

  function changeList(items: typeof changes) {
    return <section className="labChangeList">{items.length ? items.map((change) => <LocalizedLabChange key={change.id} change={change} labId={labId} />) : <div className="emptyFeed">暂无相关变化。</div>}</section>;
  }

  return (
    <>
      <section className="radarHero labHero"><div><div className="eyebrow">MY LAB · {labName.toUpperCase()}</div><h1>本周有哪些变化值得关注？</h1><p><span data-i18n-en="The system filters signals from the companies, professors, and conferences you follow, showing only changes relevant to" data-i18n-ja="システムはフォロー中の企業・教授・学会からシグナルを抽出し、" data-i18n-zh="系统从你关注的企业、教授和学术会议中筛选信号，只把与"> </span>{labName}<span data-i18n-en=" research scope." data-i18n-ja="の研究範囲に関連する変化だけを表示します。" data-i18n-zh=" 研究范围相关的变化放到这里。"> 研究范围相关的变化放到这里。</span></p></div><div className="heroInsight"><strong>本周判断</strong><span>{changes.length ? `${labName} 本周有 ${changes.length} 条相关变化，下面会分别说明它为什么相关，以及对当前判断有什么影响。` : `${labName} 本周暂时没有新的相关变化，系统会继续观察企业、教授和学术会议的公开信号。`}</span></div></section>
      <FollowedItems initialItems={watchItems} labId={labId} />
      <div className="sectionHeading labHeading"><div><span className="sectionLabel">LAB INTERPRETATION · THIS WEEK</span><h2>本周新增</h2></div><span className="updateCount">{changes.length} 条</span></div>
      {changeList(changes)}
      <div className="sectionHeading labHeading weeklyLabHeading"><div><span className="sectionLabel">THIS MONTH</span><h2>本月新增</h2></div><span className="updateCount">{monthChanges.length} 条</span></div>
      {changeList(monthChanges)}
      <SnowyAssistant labId={labId} labName={labName} />
    </>
  );
}
