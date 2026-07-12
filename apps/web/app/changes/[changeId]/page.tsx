import Link from "next/link";
import { getChange, getDocument, type DocumentRecord } from "../../lib/api";
import ArticleLanguagePanel from "../../ArticleLanguagePanel";
import { getCurrentUser, getLabTodayChanges } from "../../lib/serverApi";
import { redirect } from "next/navigation";
import SnowyAssistant from "../../labs/[labId]/SnowyAssistant";
import SnowyArticleButton from "../../SnowyArticleButton";

export const dynamic = "force-dynamic";

function formatDate(value: string | null | undefined) {
  if (!value) return "未提供";
  return new Intl.DateTimeFormat("zh-CN", { year: "numeric", month: "short", day: "numeric" }).format(new Date(value));
}

function changeTypeLabel(change: { title: string; watch_items: string[] }) {
  const items = change.watch_items.join(" ");
  if (/Intel|Samsung|Absolics|TSMC|Corning/.test(items)) return "企业动态";
  if (/东京大学|MIT|东北大学/.test(items)) return "高校论文";
  if (/专利|patent/i.test(change.title)) return "专利";
  if (/ECTC|IEDM/.test(items)) return "学术顶会";
  return "其他技术新闻";
}

function contentLevelLabel(level: DocumentRecord["content_level"] | undefined) {
  if (level === "full_text") return "已获取全文";
  if (level === "abstract") return "已获取摘要";
  return "仅有元数据";
}

export default async function ChangePage({ params, searchParams }: { params: Promise<{ changeId: string }>; searchParams: Promise<{ lab?: string }> }) {
  const { changeId } = await params;
  const query = await searchParams;
  const user = await getCurrentUser();
  if (!user.authenticated) redirect("/");
  const labId = query.lab && user.lab_ids.includes(query.lab) ? query.lab : user.lab_ids[0];
  const labName = labId ? user.lab_names[user.lab_ids.indexOf(labId)] || "你的 Lab" : "你的 Lab";
  const [change, labChanges] = await Promise.all([getChange(changeId), labId ? getLabTodayChanges(labId) : Promise.resolve([])]);
  const labImpact = labChanges.find((item) => item.id === change.id);
  const documentIds = change.evidence.map((item) => item.document_id).filter((id): id is string => Boolean(id));
  const documents = await Promise.all(documentIds.map(async (id) => { try { return await getDocument(id); } catch { return null; } }));
  const documentsById = new Map<string, DocumentRecord>(documents.filter((document): document is DocumentRecord => Boolean(document)).map((document) => [document.id, document]));
  const snowyArticleContext = [
    `标题：${change.title}`,
    `Radar 摘要：${change.change_summary}`,
    `关键事实：${change.new_facts.join("；")}`,
    ...change.evidence.map((item) => {
      const document = item.document_id ? documentsById.get(item.document_id) : undefined;
      return `来源：${document?.title || item.source_title}\n${(document?.content_text || item.evidence_text || "").slice(0, 9000)}`;
    }),
  ].join("\n\n");

  return <>
    <Link className="backLink" href={labId ? `/labs/${labId}` : "/labs"}>← 返回 {labName}</Link>
    <header className="detailHeader detailHero"><div className="detailEyebrow"><span className="badge">{changeTypeLabel(change)}</span><span>RESEARCH RADAR · {formatDate(change.detected_at)}</span></div><h1>{change.title}</h1><div className="detailTags">{change.watch_items.filter((item) => item !== "Glass Core").map((item) => <span className="tag" key={item}>{item}</span>)}{change.affected_labs.map((lab) => <span className="tag labTag" key={lab}>{lab}</span>)}</div></header>
    <section className="detailGrid richDetailGrid">
      <article className="detailMain rawArticleColumn">{change.evidence.map((item) => { const document = item.document_id ? documentsById.get(item.document_id) : undefined; const url = document?.canonical_url || item.url; return <ArticleLanguagePanel key={item.source_id + item.evidence_text} changeId={change.id} sourceTitle={document?.title || item.source_title || change.title} sourceContent={document?.content_text || item.evidence_text || "来源未提供正文内容。"} sourceSummary={change.change_summary} sourceFacts={change.new_facts} sourceType={document?.source_type || "公开来源"} date={formatDate(document?.published_at)} author={document?.authors?.length ? document.authors.join("、") : "来源未提供"} source={document?.source_title || item.source_title} url={url} labImpact={Boolean(labImpact)} aiGenerated={Boolean(labImpact?.ai_generated)} />; })}</article>
      <aside className="detailAside richDetailAside"><div className="asideSection integratedInsight"><div className="integratedInsightHeader"><div className="aiVerdictHeader"><span className="sectionLabel">{labImpact?.ai_generated ? "AI ASSESSMENT" : "RADAR ASSESSMENT"}</span><span className="aiStatus"><span className="statusDot" /> 已完成</span></div><div className="snowyDeepAction"><SnowyArticleButton context={snowyArticleContext} label="让 Snowy 深度分析" compact /></div></div><div className="aiRightPanel aiCompact"><h2>{labImpact?.ai_generated ? "AI 判断" : "Radar 判断"}</h2><p>{change.change_summary}</p><ul className="aiFactList">{change.new_facts.slice(0, 2).map((fact) => <li key={fact}>{fact}</li>)}</ul><small>{labImpact?.ai_generated ? `由 ${labImpact.ai_provider} 生成` : "由 Radar 规则结合研究范围生成"}。</small></div></div></aside>
    </section>
    <div className="detailProvenance bottomProvenance"><div><span className="sectionLabel">PROVENANCE</span><p>这条信息由 Research Radar 从公开来源发现，原文内容和链接均保留用于追溯。</p></div><span className="provenanceStatus"><span className="statusDot" /> SOURCE TRACEABLE</span></div>
    {labId && <SnowyAssistant labId={labId} labName={labName} />}
  </>;
}
