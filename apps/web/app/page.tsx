import Link from "next/link";
import { getTodayChanges, getWatchItems } from "./lib/api";
import DashboardFeed from "./DashboardFeed";

export const dynamic = "force-dynamic";
const importanceStars: Record<string, string> = { S: "★★★★★", A: "★★★★☆", B: "★★★☆☆", C: "★★☆☆☆" };

export default async function Home() {
  const [changes, watchItems] = await Promise.all([getTodayChanges(), getWatchItems()]);
  const followed = watchItems.filter((item) => item.is_following);
  return <>
    <section className="radarHero"><div><div className="eyebrow">AI RESEARCH RADAR · DAILY INTELLIGENCE</div><h1>今天发生了什么？</h1><p>系统每天扫描你的关注对象，只把值得专家打开的变化推到这里。</p></div><div className="heroInsight"><strong>核心判断</strong><span>Glass Core 正从展示型信号进入工程验证阶段，量产成熟度值得持续跟踪。</span></div></section>
    <section className="followStrip"><span className="sectionLabel">正在关注</span>{followed.map((item) => <Link className="tag" href={item.kind === "company" ? `/companies#${item.id}` : `/topics#${item.id}`} key={item.id}>{item.name}</Link>)}</section>
    <DashboardFeed changes={changes} />
  </>;
}
