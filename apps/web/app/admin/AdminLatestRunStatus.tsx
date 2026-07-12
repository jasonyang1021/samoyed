"use client";

import { useEffect, useState } from "react";
import { getRadarRuns, type RadarRun } from "../lib/api";

const labels: Record<RadarRun["status"], string> = {
  running: "Processing",
  completed: "Normal",
  completed_with_errors: "Partial",
  failed: "Failed",
};

export default function AdminLatestRunStatus({ initialRun }: { initialRun?: RadarRun }) {
  const [latest, setLatest] = useState(initialRun);

  useEffect(() => {
    let cancelled = false;
    const refresh = async () => {
      try {
        const runs = await getRadarRuns();
        if (!cancelled && runs[0]) setLatest(runs[0]);
      } catch {
        // The pipeline panel owns the detailed error state; keep the last KPI.
      }
    };
    void refresh();
    const timer = window.setInterval(() => void refresh(), 3000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, []);

  return <strong aria-live="polite">{latest ? labels[latest.status] : "Not run"}</strong>;
}
