"use client";

import { useEffect, useRef, useState } from "react";
import { getRadarRuns, runRadar, type AIStatus, type RadarRun } from "../lib/api";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

const statusLabel: Record<RadarRun["status"], string> = { running: "运行中", completed: "已完成", completed_with_errors: "部分完成", failed: "失败" };

export default function RadarRunPanel({ initialRuns, aiStatus }: { initialRuns: RadarRun[]; aiStatus: AIStatus }) {
  const [runs, setRuns] = useState(initialRuns);
  const [running, setRunning] = useState(initialRuns[0]?.status === "running");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const userStartedRun = useRef(false);

  useEffect(() => {
    if (!running) return;
    let cancelled = false;
    const refresh = async () => {
      try {
        const latestRuns = await getRadarRuns();
        if (cancelled) return;
        setRuns(latestRuns);
        if (!userStartedRun.current) setRunning(latestRuns[0]?.status === "running");
      } catch {
        // Keep the button locked while the run is active if polling temporarily fails.
      }
    };
    void refresh();
    const timer = window.setInterval(() => void refresh(), 3000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, [running]);

  async function handleRun() {
    if (running) return;
    userStartedRun.current = true;
    setRunning(true);
    setError("");
    setNotice("");
    let accepted = false;
    try {
      const result = await runRadar();
      accepted = result.status === "running";
      setRuns((current) => [result, ...current.filter((run) => run.id !== result.id)]);
      setRunning(accepted);
      setNotice(result.status === "running"
        ? "雷达任务已启动，正在后台抓取和分析，页面会自动刷新进度。"
        : result.status === "completed"
        ? `运行成功：抓取 ${result.documents_fetched} 条，新增 ${result.documents_created} 条，生成 ${result.generated_changes} 条变化。`
        : result.status === "completed_with_errors"
          ? `运行完成，但有 ${result.errors.length} 个来源异常：抓取 ${result.documents_fetched} 条，新增 ${result.documents_created} 条。`
          : `运行失败${result.errors.length ? `：${result.errors.join("；")}` : "，请查看运行记录。"}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "运行失败，请检查来源状态或稍后再试。");
    } finally {
      userStartedRun.current = false;
      if (!accepted) setRunning(false);
    }
  }

  const latest = runs[0];
  const phaseLabels: Record<RadarRun["phase"], string> = { starting: "准备中", ingestion: "抓取来源", ai_search: "AI 检索", analysis: "分析资料", completed: "已完成", failed: "失败" };
  const progressText = latest?.phase === "ingestion"
    ? `正在处理来源 ${latest.processed_sources} / ${latest.total_sources}：${latest.current_source || "准备中"}`
    : latest?.phase === "ai_search"
      ? `正在进行 ${phaseLabels.ai_search}：${latest.current_source || "AI Web Search"}`
      : latest?.phase === "analysis"
        ? `正在${phaseLabels.analysis}：已分析 ${latest.analyzed} / ${latest.analysis_total} 条；Dify 请求 ${latest.dify_requests_succeeded} 成功 / ${latest.dify_requests_total} 次，${latest.dify_requests_failed} 失败`
    : latest?.status === "completed_with_errors"
      ? `运行已结束：${latest.errors.length} 个来源或阶段异常，结果已保留。`
      : latest?.status === "failed"
        ? "运行失败：请查看下方错误详情。"
        : "正在准备运行任务。";
  return <>
    <section className="radarControlBar"><div><span className="sectionLabel">PIPELINE</span><h2>Research Radar Pipeline</h2><p>Sources → Documents → AI Analysis → Changes</p><span className={`aiMode ${aiStatus.configured ? "enabled" : "fallback"}`}>{aiStatus.configured ? `AI 已启用 · ${aiStatus.provider === "dify" ? "Dify Workflow" : aiStatus.model}${aiStatus.web_search_enabled ? " · 含联网检索" : ""}` : "当前为规则分析 · 配置 AI Provider 后启用"}</span>{running && <div className="radarProgress"><span className="radarRunningHint">{progressText}</span><div className="radarProgressTrack" role="progressbar" aria-label="雷达运行进度"><span /></div></div>}</div><button className="runRadarButton" onClick={handleRun} disabled={running}>{running ? "运行中，请稍候..." : "运行雷达 →"}</button></section>
    {error && <p className="radarError">{error}</p>}
    {notice && <p className={`radarRunNotice ${latest?.status || "completed"}`}>{notice}</p>}
    {latest && <section className="runSummary"><div><span className="sectionLabel">LAST RUN</span><strong>{statusLabel[latest.status]}</strong><small>{formatDate(latest.started_at)}</small></div><div><strong>{latest.source_count}</strong><small>个来源</small></div><div><strong>{latest.documents_created}</strong><small>新增资料</small></div><div><strong>{latest.relevant}</strong><small>相关资料</small></div><div><strong>{latest.generated_changes}</strong><small>生成变化</small></div></section>}
    <section className="runHistory"><div className="sectionHeading"><div><span className="sectionLabel">RUN HISTORY</span><h2>运行记录</h2></div></div>{runs.length === 0 ? <div className="emptyFeed">还没有运行记录。</div> : runs.map((run) => <article className="runRow" key={run.id}><div><span className={`runStatus ${run.status}`}>{statusLabel[run.status]}</span><strong>{formatDate(run.started_at)}</strong></div><div><span>{run.source_count} 来源</span><span>{run.documents_fetched} 抓取</span><span>{run.documents_created} 新增</span><span>{run.relevant} 相关</span><span>{run.generated_changes} Changes</span></div>{run.errors.length > 0 && <p>{run.errors.join("；")}</p>}</article>)}</section>
  </>;
}
