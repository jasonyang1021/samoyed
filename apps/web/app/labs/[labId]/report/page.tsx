import { getLabTodayChanges, getLabMonthChanges } from "../../../lib/api";
import { getCurrentUser, getLab, getLabWatchItems } from "../../../lib/serverApi";
import { redirect } from "next/navigation";

export const dynamic = "force-dynamic";

export default async function LabInsightReport({ params }: { params: Promise<{ labId: string }> }) {
  const user = await getCurrentUser();
  if (!user.authenticated) redirect("/");
  const { labId } = await params;
  if (!user.lab_ids.includes(labId)) redirect("/");
  const [lab, today, month, watchItems] = await Promise.all([getLab(labId), getLabTodayChanges(labId), getLabMonthChanges(labId), getLabWatchItems(labId)]);
  const date = new Intl.DateTimeFormat("zh-CN", { dateStyle: "long" }).format(new Date());
  const items = watchItems.filter((item) => item.is_following);
  const reportItems = [...today, ...month];
  return <main className="reportPage"><header className="reportHeader"><div><span className="reportKicker">AI RESEARCH RADAR · INSIGHT REPORT</span><h1>{lab.name} 洞察报告</h1><p>{date} · 基于关注对象、公开资料和 Lab 相关性判断生成</p></div><button className="reportPrint" type="button">打印 / 导出 PDF</button></header><section className="reportExecutive"><span className="reportKicker">EXECUTIVE VIEW</span><h2>今天最值得关注的变化</h2><p>{today.length ? `${lab.name} 今日识别到 ${today.length} 条相关变化。信号主要来自 ${items.slice(0, 4).map((item) => item.name).join("、") || "当前关注对象"}，建议优先查看高影响变化及其原始来源。` : `${lab.name} 今日没有新的相关变化，建议继续观察本月信号是否形成连续证据。`}</p></section><section className="reportStats"><div><strong>{today.length}</strong><span>今日新增</span></div><div><strong>{month.length}</strong><span>本月更早变化</span></div><div><strong>{items.length}</strong><span>正在关注</span></div><div><strong>{reportItems.filter((item) => item.ai_generated).length}</strong><span>AI 生成 Lab 判断</span></div></section><section className="reportSection"><div className="reportSectionHeader"><span className="reportKicker">SIGNALS</span><h2>重点变化</h2></div>{reportItems.length ? reportItems.map((item) => <article className="reportSignal" key={`${item.id}-${item.detected_at}`}><div className="reportSignalTop"><span className={`reportImportance importance-${item.importance}`}>{item.importance}</span><span>{item.ai_generated ? `AI · ${item.ai_provider}` : "规则结合 Lab 范围"}</span></div><h3>{item.title}</h3><p className="reportSummary">{item.change_summary}</p><div className="reportInsightGrid"><div><b>为什么相关</b><p>{item.why_relevant}</p></div><div><b>判断影响</b><p>{item.impact}</p></div></div></article>) : <p className="reportEmpty">暂无可汇总的变化。</p>}</section><footer className="reportFooter">研究雷达保留原始来源链接。该报告用于研究跟踪与讨论，不替代专家判断。</footer><script dangerouslySetInnerHTML={{ __html: "document.querySelector('.reportPrint')?.addEventListener('click', () => window.print())" }} /></main>;
}
