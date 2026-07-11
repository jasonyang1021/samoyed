import Link from "next/link";
import { redirect } from "next/navigation";
import { getCurrentUser, getLab, getLabWatchItems } from "../../../lib/serverApi";
import LabSettingsPanel from "./LabSettingsPanel";

export const dynamic = "force-dynamic";

export default async function LabSettingsPage({ params }: { params: Promise<{ labId: string }> }) {
  const { labId } = await params;
  const user = await getCurrentUser();
  if (!user.authenticated || (user.role !== "system_admin" && user.role !== "lab_admin")) redirect(`/labs/${labId}`);
  const [lab, items] = await Promise.all([getLab(labId), getLabWatchItems(labId)]);
  const labName = lab.name;
  return <><Link className="backLink" href={`/labs/${labId}`}>← 返回 {labName}</Link><div className="settingsPageHeader"><span className="sectionLabel">MY LAB / SETTINGS</span><h1>{labName} 设置</h1><p>定制本 Lab 的关注企业、教授、高校和研究主题。</p></div><LabSettingsPanel labId={labId} initialItems={items} /></>;
}
