import { getAdminAIStatus, getAdminInvitations, getAdminMemberships, getAdminRadarRuns, getAdminScheduleSettings, getAdminSources, getLabs } from "../lib/serverApi";
import InvitationPanel from "./InvitationPanel";
import LabManagementPanel from "./LabManagementPanel";
import MembershipPanel from "./MembershipPanel";
import RadarRunPanel from "./RadarRunPanel";
import ScheduleSettingsPanel from "./ScheduleSettingsPanel";
import SourcePanel from "./SourcePanel";

export const dynamic = "force-dynamic";

export default async function Admin() {
  const [runs, aiStatus, scheduleSettings, memberships, invitations, labs, sources] = await Promise.all([getAdminRadarRuns(), getAdminAIStatus(), getAdminScheduleSettings(), getAdminMemberships(), getAdminInvitations(), getLabs(), getAdminSources()]);
  return <><div className="adminPageHeader"><div><span className="badge">RADAR CONTROL</span><p className="muted">管理每日研究雷达、Lab 访问权限和自动运行。</p></div><div className="adminHeaderStatus"><span className="statusDot" />系统正常<small>AI {aiStatus.configured ? "已连接" : "待配置"}</small></div></div><div className="adminKpis"><div><span>研究 Lab</span><strong>{labs.length}</strong></div><div><span>成员</span><strong>{memberships.length}</strong></div><div><span>数据来源</span><strong>{sources.length}</strong></div><div><span>最近运行</span><strong>{runs.length ? runs[0].status === "completed" ? "正常" : "处理中" : "未运行"}</strong></div></div><SourcePanel sources={sources} /><LabManagementPanel initialLabs={labs} /><ScheduleSettingsPanel initialSettings={scheduleSettings} /><div className="adminTwoCol"><MembershipPanel initialMemberships={memberships} /><InvitationPanel initialInvitations={invitations} /></div><RadarRunPanel initialRuns={runs} aiStatus={aiStatus} /></>;
}
