import { cookies } from "next/headers";
import type { AIStatus, AuthUser, Lab, LabInvitation, LabMembership, RadarRun, ScheduleSettings, SourceRecord, WatchItem } from "./api";

const base = process.env.API_INTERNAL_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

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
export function getLab(labId: string) { return serverGet<Lab>(`/api/labs/${labId}`); }
export function getLabWatchItems(labId: string) { return serverGet<WatchItem[]>(`/api/labs/${labId}/watch-items`); }
export function getAdminSources() { return serverGet<SourceRecord[]>("/api/admin/sources"); }

export async function getCurrentUser() {
  const cookieStore = await cookies();
  const response = await fetch(`${base}/api/auth/me`, { headers: { cookie: cookieStore.toString() }, cache: "no-store" });
  return response.json() as Promise<AuthUser>;
}
