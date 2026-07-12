export type Evidence = {
  source_id: string;
  source_title: string;
  evidence_text: string;
  url: string | null;
  document_id?: string;
};

export type DocumentRecord = {
  id: string;
  source_id: string;
  canonical_url: string;
  title: string;
  content_text: string;
  authors: string[];
  content_level: "full_text" | "abstract" | "metadata";
  published_at: string | null;
  fetched_at: string;
  status: string;
  source_title: string;
  source_type: string;
  source_url: string | null;
};

export type SourceRecord = {
  id: string;
  source_type: string;
  title: string;
  url: string | null;
  format: string | null;
  document_count: number;
  latest_published_at: string | null;
  latest_fetched_at: string | null;
  status: string;
  enabled: boolean;
  last_error: string | null;
  last_checked_at: string | null;
};

export type LabAuditLog = {
  id: string;
  lab_id: string;
  actor_name: string | null;
  actor_email: string | null;
  action: string;
  target: string | null;
  details: Record<string, unknown>;
  created_at: string;
};

export type RadarRun = {
  id: string;
  started_at: string;
  finished_at: string | null;
  status: "running" | "completed" | "completed_with_errors" | "failed";
  source_count: number;
  documents_fetched: number;
  documents_created: number;
  analyzed: number;
  relevant: number;
  generated_changes: number;
  errors: string[];
};

export type AIStatus = {
  configured: boolean;
  provider: "dify" | "openai" | "rule_based";
  model: string;
  web_search_enabled: boolean;
};

export type AuthUser = {
  authenticated: boolean;
  email: string | null;
  name: string | null;
  picture: string | null;
  role: string;
  oauth_configured?: boolean;
  lab_ids: string[];
  lab_names: string[];
};

export type Lab = { id: string; name: string; description: string | null; admin_email?: string | null; admin_name?: string | null };

export type ScheduleSettings = {
  enabled: boolean;
  run_time: string;
  timezone: string;
  last_run_date: string | null;
  updated_at: string;
};

export type LabMembership = {
  user_id: string;
  lab_id: string;
  lab_name: string;
  email: string;
  name: string | null;
  role: "lab_admin" | "lab_user";
};

export type LabInvitation = {
  id: string;
  email: string;
  lab_id: string;
  lab_name: string;
  role: "lab_admin" | "lab_user";
  status: "pending" | "accepted";
  created_at: string;
};

export type ChangeCard = {
  id: string;
  title: string;
  new_facts: string[];
  change_summary: string;
  previous_state: string;
  current_state: string;
  importance: "S" | "A" | "B" | "C";
  evidence: Evidence[];
  next_watch_points: string[];
  affected_labs: string[];
  watch_items: string[];
  detected_at: string;
  published_at: string | null;
};

export type WatchItem = {
  id: string;
  kind: "topic" | "company" | "university" | "professor" | "conference" | "ai_recommendation";
  name: string;
  description: string | null;
  is_following: boolean;
  created_at: string;
};

export type LabChangeCard = ChangeCard & {
  why_relevant: string;
  impact: string;
  lab_next_watch_points: string[];
  ai_generated: boolean;
  ai_provider: string;
};

function apiBaseUrl() {
  if (typeof window !== "undefined") {
    return process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
  }
  return process.env.API_INTERNAL_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

// Dynamic route params may already contain percent-encoded UTF-8 characters.
// Normalize first so every Lab ID is encoded exactly once for API requests.
function labPathSegment(labId: string) {
  return encodeURIComponent(decodeURIComponent(labId));
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl()}${path}`, { cache: "no-store" });

  if (!response.ok) {
    throw new Error(`API request failed: ${path}`);
  }

  return response.json() as Promise<T>;
}

async function postJson<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${apiBaseUrl()}${path}`, { method: "POST", headers: body ? { "Content-Type": "application/json" } : undefined, body: body ? JSON.stringify(body) : undefined, credentials: "include", cache: "no-store" });

  if (!response.ok) {
    throw new Error(`API request failed: ${path}`);
  }

  return response.json() as Promise<T>;
}

async function putJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${apiBaseUrl()}${path}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), credentials: "include", cache: "no-store" });

  if (!response.ok) {
    throw new Error(`API request failed: ${path}`);
  }

  return response.json() as Promise<T>;
}

export function getTodayChanges() {
  return fetchJson<ChangeCard[]>("/api/changes/today");
}

export function getMonthlyChanges() {
  return fetchJson<ChangeCard[]>("/api/changes/month");
}

export function getLabs() {
  return fetchJson<Lab[]>("/api/labs");
}

export function getLabTodayChanges(labId: string) {
  return fetchJson<LabChangeCard[]>(`/api/labs/${labPathSegment(labId)}/changes/today`);
}

export function getLabWeekChanges(labId: string) {
  return fetchJson<LabChangeCard[]>(`/api/labs/${labPathSegment(labId)}/changes/week`);
}

export function getLabMonthChanges(labId: string) {
  return fetchJson<LabChangeCard[]>(`/api/labs/${labPathSegment(labId)}/changes/month`);
}

export function getWatchItems() {
  return fetchJson<WatchItem[]>("/api/watch-items");
}

export function getLabWatchItems(labId: string) {
  return fetchJson<WatchItem[]>(`/api/labs/${labPathSegment(labId)}/watch-items`);
}

export async function addLabWatchItem(labId: string, payload: Pick<WatchItem, "kind" | "name" | "description">) {
  const response = await fetch(`${apiBaseUrl()}/api/labs/${labPathSegment(labId)}/watch-items`, { method: "POST", headers: { "Content-Type": "application/json" }, credentials: "include", body: JSON.stringify(payload) });
  if (!response.ok) throw new Error("API request failed");
  return response.json() as Promise<WatchItem>;
}

export async function removeLabWatchItem(labId: string, watchItemId: string) {
  const response = await fetch(`${apiBaseUrl()}/api/labs/${labPathSegment(labId)}/watch-items/${encodeURIComponent(watchItemId)}`, { method: "DELETE", credentials: "include" });
  if (!response.ok) throw new Error("API request failed");
}

export function getChange(changeId: string) {
  return fetchJson<ChangeCard & { status: string }>(`/api/changes/${changeId}`);
}

export function getDocument(documentId: string) {
  return fetchJson<DocumentRecord>(`/api/documents/${documentId}`);
}

export function getRadarRuns() {
  return fetchJson<RadarRun[]>("/api/radar/runs");
}

export function getAIStatus() {
  return fetchJson<AIStatus>("/api/ai/status");
}

export function getScheduleSettings() {
  return fetchJson<ScheduleSettings>("/api/admin/schedule");
}

export function updateScheduleSettings(payload: Pick<ScheduleSettings, "enabled" | "run_time" | "timezone">) {
  return putJson<ScheduleSettings>("/api/admin/schedule", payload);
}

export function updateMembership(userId: string, labId: string, role: LabMembership["role"]) {
  return putJson<LabMembership>(`/api/admin/memberships/${encodeURIComponent(userId)}/${encodeURIComponent(labId)}`, { role });
}

export function updateLabMembership(labId: string, userId: string, role: LabMembership["role"]) {
  return putJson<LabMembership>(`/api/labs/${encodeURIComponent(labId)}/memberships/${encodeURIComponent(userId)}`, { role });
}

export function createLabInvitation(payload: Pick<LabInvitation, "email" | "lab_id" | "role">) {
  return postJson<LabInvitation>(`/api/labs/${encodeURIComponent(payload.lab_id)}/invitations`, payload);
}

export async function deleteSource(sourceId: string) {
  const response = await fetch(`${apiBaseUrl()}/api/admin/sources/${encodeURIComponent(sourceId)}`, { method: "DELETE", credentials: "include" });
  if (!response.ok) throw new Error("API request failed");
}

export function setSourceEnabled(sourceId: string, enabled: boolean) {
  return putJson<SourceRecord>(`/api/admin/sources/${encodeURIComponent(sourceId)}/enabled?enabled=${enabled}`, {});
}

export function runSource(sourceId: string) {
  return postJson<{ status: string; fetched: number; created: number; duplicates: number; error?: string }>(`/api/admin/sources/${encodeURIComponent(sourceId)}/run`);
}

export function testSource(sourceId: string) {
  return postJson<{ ok: boolean; message: string; error?: string }>(`/api/admin/sources/${encodeURIComponent(sourceId)}/test`);
}

export function getLabAuditLogs(labId: string) {
  return fetchJson<LabAuditLog[]>(`/api/labs/${encodeURIComponent(labId)}/audit-logs`);
}

export function createLab(payload: { name: string; description: string; admin_email?: string }) {
  return postJson<Lab>("/api/admin/labs", payload);
}

export function updateLab(labId: string, payload: { name: string; description: string; admin_email?: string }) {
  return putJson<Lab>(`/api/admin/labs/${encodeURIComponent(labId)}`, payload);
}

export async function deleteLab(labId: string) {
  const response = await fetch(`${apiBaseUrl()}/api/admin/labs/${encodeURIComponent(labId)}`, { method: "DELETE", credentials: "include" });
  if (!response.ok) throw new Error("API request failed");
}

export function createInvitation(payload: Pick<LabInvitation, "email" | "lab_id" | "role">) {
  return postJson<LabInvitation>("/api/admin/invitations", payload);
}

export async function runRadar() {
  return postJson<RadarRun>("/api/radar/run");
}
