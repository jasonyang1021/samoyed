import {
  getAdminAIStatus,
  getAdminRadarRuns,
  getAdminScheduleSettings,
  getAdminSources,
  getCurrentUser,
  getLabs,
} from "../lib/serverApi";
import LabManagementPanel from "./LabManagementPanel";
import RadarRunPanel from "./RadarRunPanel";
import ScheduleSettingsPanel from "./ScheduleSettingsPanel";
import SourcePanel from "./SourcePanel";

export const dynamic = "force-dynamic";

export default async function Admin() {
  const user = await getCurrentUser();
  if (user.oauth_configured && (!user.authenticated || user.role !== "system_admin")) {
    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
    return (
      <section className="emptyFeed">
        <span className="badge">ADMIN</span>
        <h1>Administrator access required</h1>
        <p className="muted">Please sign in with a configured administrator Google account.</p>
        <a className="primaryLink" href={`${apiBase}/api/auth/google/start`}>Google sign in</a>
      </section>
    );
  }

  const [runs, aiStatus, scheduleSettings, labs, sources] = await Promise.all([
    getAdminRadarRuns(),
    getAdminAIStatus(),
    getAdminScheduleSettings(),
    getLabs(),
    getAdminSources(),
  ]);

  const latestRunStatus = runs.length ? (runs[0].status === "completed" ? "Normal" : "Processing") : "Not run";

  return (
    <>
      <div className="adminPageHeader">
        <div>
          <span className="badge">RADAR CONTROL</span>
          <p className="muted">Manage the daily research radar, Lab access, data sources, and scheduled runs.</p>
        </div>
        <div className="adminHeaderStatus">
          <span className="statusDot" />System online
          <small>AI {aiStatus.configured ? `connected via ${aiStatus.provider}` : "pending configuration"}</small>
        </div>
      </div>
      <div className="adminKpis">
        <div><span>Research Labs</span><strong>{labs.length}</strong></div>
        <div><span>Sources</span><strong>{sources.length}</strong></div>
        <div><span>Latest Run</span><strong>{latestRunStatus}</strong></div>
      </div>
      <LabManagementPanel initialLabs={labs} />
      <ScheduleSettingsPanel initialSettings={scheduleSettings} />
      <SourcePanel sources={sources} />
      <RadarRunPanel initialRuns={runs} aiStatus={aiStatus} />
    </>
  );
}
