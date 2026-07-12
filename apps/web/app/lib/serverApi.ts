import { cookies } from "next/headers";
import type { AIStatus, AuthUser, Lab, LabAuditLog, LabChangeCard, LabInvitation, LabMembership, RadarRun, ScheduleSettings, SourceRecord, WatchItem } from "./api";

const base = process.env.API_INTERNAL_BASE_URL ?? "http://localhost:8000";

// Next route params can already contain percent-encoded UTF-8 characters.
// Decode before encoding so a lab id is encoded exactly once in API URLs.
function labPathSegment(labId: string) {
  return encodeURIComponent(decodeURIComponent(labId));
}

async function serverGet<T>(path: string): Promise<T> {
  const cookieStore = await cookies();
  const response = await fetch(`${base}${path}`, { headers: { cookie: cookieStore.toString() }, cache: "no-store" });
  if (!response.ok) throw new Error(`API request failed: ${path}`);
  return response.json() as Promise<T>;
}

export function getAdminRadarRuns() { return serverGet<RadarRun[]>("/api/radar/runs"); }
export function getAdminAIStatus() { return serverGet<AIStatus>("/api/ai/status"); }
export function getAdminScheduleSettings() { return serverGet<ScheduleSettings>("/api/admin/schedule"); }
export function getAdminMemberships() { return serverGet<LabMembership[]>("/api/admin/memberships"); }
export function getAdminInvitations() { return serverGet<LabInvitation[]>("/api/admin/invitations"); }
export function getLabs() { return serverGet<Lab[]>("/api/labs"); }
export function getLab(labId: string) { return serverGet<Lab>(`/api/labs/${labPathSegment(labId)}`); }
export function getLabWatchItems(labId: string) { return serverGet<WatchItem[]>(`/api/labs/${labPathSegment(labId)}/watch-items`); }
export function getLabTodayChanges(labId: string) { return serverGet<LabChangeCard[]>(`/api/labs/${labPathSegment(labId)}/changes/today`); }
export function getLabWeekChanges(labId: string) { return serverGet<LabChangeCard[]>(`/api/labs/${labPathSegment(labId)}/changes/week`); }
export function getLabMonthChanges(labId: string) { return serverGet<LabChangeCard[]>(`/api/labs/${labPathSegment(labId)}/changes/month`); }
export function getAdminSources() { return serverGet<SourceRecord[]>("/api/admin/sources"); }
export function getLabMemberships(labId: string) { return serverGet<LabMembership[]>(`/api/labs/${labPathSegment(labId)}/memberships`); }
export function getLabInvitations(labId: string) { return serverGet<LabInvitation[]>(`/api/labs/${labPathSegment(labId)}/invitations`); }
export function getLabAuditLogs(labId: string) { return serverGet<LabAuditLog[]>(`/api/labs/${labPathSegment(labId)}/audit-logs`); }

export async function getCurrentUser() {
  const cookieStore = await cookies();
  const response = await fetch(`${base}/api/auth/me`, { headers: { cookie: cookieStore.toString() }, cache: "no-store" });
  return response.json() as Promise<AuthUser>;
}
