import { getTodayChanges, getWatchItems } from "../lib/api";

export const dynamic = "force-dynamic";
export default async function CompaniesPage() {
  const [items, changes] = await Promise.all([getWatchItems(), getTodayChanges()]);
  const companies = items.filter((item) => item.kind === "company");
  return <><div className="pageIntro"><span className="badge">COMPANIES</span><h1>企业动态</h1><p className="muted">关注企业路线、产品信号、合作公告与量产进展。</p></div><section className="companyList">{companies.map((company) => { const related = changes.filter((change) => change.watch_items.includes(company.id)); return <article className="companyRow" id={company.id} key={company.id}><div><span className="sectionLabel">COMPANY</span><h2>{company.name}</h2><p className="muted">{company.description}</p></div><div className="companySignal"><strong>{related.length}</strong><span>条今日相关变化</span>{related[0] && <p>{related[0].title}</p>}</div></article>; })}</section></>;
}
