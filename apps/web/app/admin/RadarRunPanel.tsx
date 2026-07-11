"use client";

import { useState } from "react";
import { runRadar, type AIStatus, type RadarRun } from "../lib/api";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

const statusLabel: Record<RadarRun["status"], string> = { running: "运行中", completed: "已完成", completed_with_errors: "部分完成", failed: "失败" };

export default function RadarRunPanel({ initialRuns, aiStatus }: { initialRuns: RadarRun[]; aiStatus: AIStatus }) {
  const [runs, setRuns] = useState(initialRuns);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  async function handleRun() {
    setRunning(true);
    setError("");
    try {
      const result = await runRadar();
      setRuns((current) => [result, ...current.filter((run) => run.id !== result.id)]);
    } catch {
      setError("运行失败，请检查来源状态或稍后再试。");
    } finally {
      setRunning(false);
    }
  }

  const latest = runs[0];
  return <>
    <section className="radarControlBar"><div><span className="sectionLabel">PIPELINE</span><h2>Research Radar Pipeline</h2><p>Sources → Documents → AI Analysis → Changes</p><span className={`aiMode ${aiStatus.configured ? "enabled" : "fallback"}`}>{aiStatus.configured ? `AI 已启用 · ${aiStatus.provider === "dify" ? "Dify Workflow" : aiStatus.model}${aiStatus.web_search_enabled ? " · 含联网检索" : ""}` : "当前为规则分析 · 配置 AI Provider 后启用"}</span></div><button className="runRadarButton" onClick={handleRun} disabled={running}>{running ? "运行中..." : "运行雷达 →"}</button></section>
    {error && <p className="radarError">{error}</p>}
    {latest && <section className="runSummary"><div><span className="sectionLabel">LAST RUN</span><strong>{statusLabel[latest.status]}</strong><small>{formatDate(latest.started_at)}</small></div><div><strong>{latest.source_count}</strong><small>个来源</small></div><div><strong>{latest.documents_created}</strong><small>新增资料</small></div><div><strong>{latest.relevant}</strong><small>相关资料</small></div><div><strong>{latest.generated_changes}</strong><small>生成变化</small></div></section>}
    <section className="runHistory"><div className="sectionHeading"><div><span className="sectionLabel">RUN HISTORY</span><h2>运行记录</h2></div></div>{runs.length === 0 ? <div className="emptyFeed">还没有运行记录。</div> : runs.map((run) => <article className="runRow" key={run.id}><div><span className={`runStatus ${run.status}`}>{statusLabel[run.status]}</span><strong>{formatDate(run.started_at)}</strong></div><div><span>{run.source_count} 来源</span><span>{run.documents_fetched} 抓取</span><span>{run.documents_created} 新增</span><span>{run.relevant} 相关</span><span>{run.generated_changes} Changes</span></div>{run.errors.length > 0 && <p>{run.errors.join("；")}</p>}</article>)}</section>
  </>;
}
