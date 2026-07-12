import Link from "next/link";
import { redirect } from "next/navigation";
import { getCurrentUser, getLab, getLabAuditLogs, getLabInvitations, getLabMemberships, getLabWatchItems } from "../../../lib/serverApi";
import LabSettingsPanel from "./LabSettingsPanel";
import MembershipPanel from "../../../admin/MembershipPanel";
import InvitationPanel from "../../../admin/InvitationPanel";
import AuditLogPanel from "./AuditLogPanel";

export const dynamic = "force-dynamic";

export default async function LabSettingsPage({ params }: { params: Promise<{ labId: string }> }) {
  const { labId } = await params;
  const user = await getCurrentUser();
  if (!user.authenticated || (user.role !== "system_admin" && (!user.lab_ids.includes(labId) || user.role !== "lab_admin"))) redirect(`/labs/${labId}`);
  const [lab, items, memberships, invitations, auditLogs] = await Promise.all([getLab(labId), getLabWatchItems(labId), getLabMemberships(labId), getLabInvitations(labId), getLabAuditLogs(labId)]);
  const labName = lab.name;
  return <><Link className="backLink" href={`/labs/${labId}`}>← 返回 {labName}</Link><div className="settingsPageHeader"><span className="sectionLabel">MY LAB / SETTINGS</span><h1>{labName} 设置</h1><p>定制本 Lab 的关注对象、成员角色和邀请。</p></div><LabSettingsPanel labId={labId} initialItems={items} /><div className="labAccessGrid"><MembershipPanel labId={labId} initialMemberships={memberships} /><InvitationPanel labId={labId} initialInvitations={invitations} /></div><AuditLogPanel entries={auditLogs} /></>;
}
