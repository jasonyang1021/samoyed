import Link from "next/link";
import { getChange } from "../../lib/api";

export const dynamic = "force-dynamic";
export default async function ChangePage({ params }: { params: Promise<{ changeId: string }> }) {
  const { changeId } = await params;
  const change = await getChange(changeId);
  return <><Link className="backLink" href="/">← 返回今日变化</Link><div className="detailHeader"><span className="badge">{change.importance}级变化</span><h1>{change.title}</h1><p className="muted">{change.change_summary}</p><div className="feedMeta">{change.watch_items.join(" · ")} · {change.affected_labs.join(" / ")}</div></div><section className="detailGrid"><article className="detailMain"><div className="detailSection"><span className="sectionLabel">NEW FACTS</span><h2>今天新增</h2><ul>{change.new_facts.map((fact) => <li key={fact}>{fact}</li>)}</ul></div><div className="stateCompare detailStates"><div><span className="sectionLabel">PREVIOUS STATE</span><p>{change.previous_state}</p></div><div><span className="sectionLabel">CURRENT STATE</span><p>{change.current_state}</p></div></div><div className="detailSection"><span className="sectionLabel">EVIDENCE</span><h2>证据来源</h2>{change.evidence.map((item) => <div className="evidence" key={item.source_id}><strong>{item.source_title}</strong><p>{item.evidence_text}</p></div>)}</div></article><aside className="detailAside"><span className="sectionLabel">NEXT WATCH</span><h2>下一步观察</h2><ul>{change.next_watch_points.map((point) => <li key={point}>{point}</li>)}</ul><Link className="primaryLink" href="/labs/lab-glass-core">查看 Glass Core Lab 判断 →</Link></aside></section></>;
}
