import Link from "next/link";
import { redirect } from "next/navigation";
import { getAdminSources, getCurrentUser } from "../../lib/serverApi";
import SourceManagementPanel from "../SourceManagementPanel";

export const dynamic = "force-dynamic";

export default async function SourcesPage() {
  const user = await getCurrentUser();
  if (user.oauth_configured && (!user.authenticated || user.role !== "system_admin")) redirect("/admin");
  const sources = await getAdminSources();
  return <><Link className="backLink" href="/admin">← 返回控制台</Link><div className="settingsPageHeader"><span className="sectionLabel">RADAR CONTROL / SOURCES</span><h1>数据来源管理</h1><p>查看来源配置、抓取状态和已入库资料；删除来源会同时清理其资料和变化。</p></div><SourceManagementPanel initialSources={sources} /></>;
}
