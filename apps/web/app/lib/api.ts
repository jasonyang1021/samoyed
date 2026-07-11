export type Evidence = {
  source_id: string;
  source_title: string;
  evidence_text: string;
  url: string | null;
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
};

export type WatchItem = {
  id: string;
  kind: "topic" | "company" | "university" | "conference";
  name: string;
  description: string | null;
  is_following: boolean;
  created_at: string;
};

export type LabChangeCard = ChangeCard & {
  why_relevant: string;
  impact: string;
  lab_next_watch_points: string[];
};

function apiBaseUrl() {
  return process.env.API_INTERNAL_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl()}${path}`, { cache: "no-store" });

  if (!response.ok) {
    throw new Error(`API request failed: ${path}`);
  }

  return response.json() as Promise<T>;
}

export function getTodayChanges() {
  return fetchJson<ChangeCard[]>("/api/changes/today");
}

export function getLabTodayChanges(labId: string) {
  return fetchJson<LabChangeCard[]>(`/api/labs/${labId}/changes/today`);
}

export function getWatchItems() {
  return fetchJson<WatchItem[]>("/api/watch-items");
}

export function getChange(changeId: string) {
  return fetchJson<ChangeCard & { status: string }>(`/api/changes/${changeId}`);
}
