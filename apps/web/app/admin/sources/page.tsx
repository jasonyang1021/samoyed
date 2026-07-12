import Link from "next/link";
import { redirect } from "next/navigation";
import { getAdminSources, getCurrentUser } from "../../lib/serverApi";
import SourceManagementPanel from "../SourceManagementPanel";
import SourceRecommendationPanel from "../SourceRecommendationPanel";

export const dynamic = "force-dynamic";

export default async function SourcesPage() {
  const user = await getCurrentUser();
  if (user.oauth_configured && (!user.authenticated || user.role !== "system_admin")) redirect("/admin");
  const sources = await getAdminSources();
  const activeSources = sources.filter((source) => source.enabled);
  return <><Link className="backLink" href="/admin">← 返回控制台</Link><div className="settingsPageHeader sourcePageHeader"><div><span className="sectionLabel">RADAR CONTROL / SOURCES</span><h1>数据来源管理</h1><p>来源按 Lab 推荐后启用；系统管理员负责维护全局来源目录。</p></div><SourceRecommendationPanel /></div>{activeSources.length ? <SourceManagementPanel initialSources={activeSources} /> : <section className="emptySourceCatalog"><strong>还没有启用的数据来源</strong><p>点击右上角“生成推荐”，按 Lab 选择需要使用的来源。</p></section>}</>;
}
