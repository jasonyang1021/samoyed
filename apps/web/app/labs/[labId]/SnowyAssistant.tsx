"use client";

import { useEffect, useRef, useState } from "react";

type SnowyResponse = {
  answer: string;
  learning_summary: string;
  conclusions: string[];
  studied_articles: string[];
  uncertainties: string[];
  suggested_questions: string[];
  source_indexes: number[];
  sources: { index: number; title: string; url: string | null }[];
  studied_count: number;
  provider: string;
  answer_source: string;
  degraded: boolean;
  web_search_used: boolean;
};

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  meta?: string;
  provider?: string;
  degraded?: boolean;
  webSearchUsed?: boolean;
};

function normalizeResponse(value: Partial<SnowyResponse>): SnowyResponse {
  return {
    answer: typeof value.answer === "string" ? value.answer : "Snowy 暂时没有形成可确认的回答。",
    learning_summary: typeof value.learning_summary === "string" ? value.learning_summary : "已读取当前 Lab 的研究上下文。",
    conclusions: Array.isArray(value.conclusions) ? value.conclusions.map(String) : [],
    studied_articles: Array.isArray(value.studied_articles) ? value.studied_articles.map(String) : [],
    uncertainties: Array.isArray(value.uncertainties) ? value.uncertainties.map(String) : [],
    suggested_questions: Array.isArray(value.suggested_questions) ? value.suggested_questions.map(String) : [],
    source_indexes: Array.isArray(value.source_indexes) ? value.source_indexes.map(Number) : [],
    sources: Array.isArray(value.sources) ? value.sources : [],
    studied_count: Number(value.studied_count) || 0,
    provider: value.provider || "unknown",
    answer_source: value.answer_source || "unknown",
    degraded: Boolean(value.degraded),
    web_search_used: Boolean(value.web_search_used),
  };
}

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
const snowyCopy = {
  zh: { open: "打开 Snowy 研究助手", close: "关闭 Snowy", collapse: "收起 Snowy", today: "今日分析", typing: "Snowy 正在阅读和整理", placeholder: "问 Snowy 一个研究问题…", send: "发送", initial: "今天的初步判断：", uncertain: "还需要确认：", web: " · 已联网检索", labOnly: " · 仅使用 Lab 数据", answered: "✓ DeepSeek Agent 已回答", fallback: "⚠ 本地规则临时结果，未经过 DeepSeek", assistantAnswered: "✓ 研究助手已回答", error: "我暂时还没连上研究资料，请稍后再试。", contextError: "学习上下文加载失败。", suggestions: ["这周有什么值得关注？", "你为什么这样判断？", "接下来应该追踪什么？"] },
  en: { open: "Open Snowy research assistant", close: "Close Snowy", collapse: "Collapse Snowy", today: "Today's analysis", typing: "Snowy is reading and organizing", placeholder: "Ask Snowy a research question…", send: "Send", initial: "Today's initial assessment: ", uncertain: "Needs confirmation: ", web: " · web searched", labOnly: " · Lab data only", answered: "✓ DeepSeek Agent answered", fallback: "⚠ Local rule result, not processed by DeepSeek", assistantAnswered: "✓ Research assistant answered", error: "I could not connect to the research materials. Please try again.", contextError: "Research context failed to load.", suggestions: ["What is worth noticing this week?", "Why did you reach that conclusion?", "What should we track next?"] },
  ja: { open: "Snowy研究アシスタントを開く", close: "Snowyを閉じる", collapse: "Snowyを閉じる", today: "今日の分析", typing: "Snowyが整理しています", placeholder: "Snowyに研究について質問…", send: "送信", initial: "今日の初期判断：", uncertain: "要確認：", web: " · ウェブ検索済み", labOnly: " · Labデータのみ", answered: "✓ DeepSeek Agentが回答", fallback: "⚠ ローカルルールの結果（DeepSeek未処理）", assistantAnswered: "✓ Research Assistantが回答", error: "研究資料に接続できませんでした。もう一度お試しください。", contextError: "研究コンテキストの読み込みに失敗しました。", suggestions: ["今週注目すべき変化は？", "なぜその判断になりましたか？", "次に何を追跡すべきですか？"] },
} as const;

export default function SnowyAssistant({ labId, labName }: { labId: string; labName: string }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [language, setLanguage] = useState("zh-CN");
  const [launcherPosition, setLauncherPosition] = useState({ x: 0, y: 0 });
  const articleLaunchRef = useRef(false);
  const messagesRef = useRef<HTMLDivElement>(null);
  const launcherPositionLoadedRef = useRef(false);
  const dragRef = useRef({ startX: 0, startY: 0, startXOffset: 0, startYOffset: 0, moved: false, dragging: false });
  const copy = snowyCopy[language === "en" ? "en" : language === "ja" ? "ja" : "zh"];

  useEffect(() => {
    setLanguage(window.localStorage.getItem("radar-language") || "zh-CN");
  }, []);

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(`snowy-launcher-position:${labId}`);
      if (saved) {
        const parsed = JSON.parse(saved) as { x?: unknown; y?: unknown };
        if (typeof parsed.x === "number" && typeof parsed.y === "number") setLauncherPosition({ x: parsed.x, y: parsed.y });
      }
    } catch {
      // Ignore unavailable or malformed local storage and use the default position.
    } finally {
      launcherPositionLoadedRef.current = true;
    }
  }, [labId]);

  useEffect(() => {
    if (!launcherPositionLoadedRef.current) return;
    try { window.localStorage.setItem(`snowy-launcher-position:${labId}`, JSON.stringify(launcherPosition)); } catch { /* Storage can be disabled by the browser. */ }
  }, [labId, launcherPosition]);

  function startLauncherDrag(event: React.PointerEvent<HTMLButtonElement>) {
    event.preventDefault();
    dragRef.current = { startX: event.clientX, startY: event.clientY, startXOffset: launcherPosition.x, startYOffset: launcherPosition.y, moved: false, dragging: true };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function moveLauncher(event: React.PointerEvent<HTMLButtonElement>) {
    if (!dragRef.current.dragging) return;
    const deltaX = event.clientX - dragRef.current.startX;
    const deltaY = event.clientY - dragRef.current.startY;
    if (Math.abs(deltaX) + Math.abs(deltaY) > 4) dragRef.current.moved = true;
    const maxX = typeof window === "undefined" ? 500 : Math.max(0, window.innerWidth - 90);
    const maxY = typeof window === "undefined" ? 500 : Math.max(0, window.innerHeight - 90);
    setLauncherPosition({
      x: Math.max(-maxX, Math.min(0, dragRef.current.startXOffset + deltaX)),
      y: Math.max(-maxY, Math.min(0, dragRef.current.startYOffset + deltaY)),
    });
  }

  function finishLauncherDrag(event: React.PointerEvent<HTMLButtonElement>) {
    dragRef.current.dragging = false;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
  }

  async function ask(nextQuestion = "", context = "") {
    const normalizedQuestion = nextQuestion.trim();
    const history = messages.slice(-10).map((message) => ({ role: message.role, content: message.content }));
    if (normalizedQuestion) setMessages((current) => [...current, { role: "user", content: normalizedQuestion }]);
    setLoading(true);
    try {
      const response = await fetch(`${apiBase}/api/labs/${labId}/assistant`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: normalizedQuestion, context: context.slice(0, 15000), history, locale: language }),
      });
      if (!response.ok) throw new Error("assistant unavailable");
      const result = normalizeResponse(await response.json());
      const analysis = normalizedQuestion ? result.answer : [result.answer, result.conclusions.length ? `${copy.initial}${result.conclusions.join(" ")}` : "", result.uncertainties.length ? `${copy.uncertain}${result.uncertainties.join(" ")}` : ""].filter(Boolean).join("\n\n");
      setMessages((current) => [...current, { role: "assistant", content: analysis, meta: result.learning_summary, provider: result.provider, degraded: result.degraded, webSearchUsed: result.web_search_used }]);
      if (result.suggested_questions.length) setSuggestions(result.suggested_questions);
    } catch {
      const result = normalizeResponse({ answer: copy.error, learning_summary: copy.contextError, suggested_questions: [...copy.suggestions] });
      setMessages((current) => [...current, { role: "assistant", content: result.answer, meta: result.learning_summary, provider: "client_error", degraded: true }]);
      setSuggestions(result.suggested_questions);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (open && messages.length === 0 && !loading && !articleLaunchRef.current) void ask();
  }, [open]);

  useEffect(() => {
    function handleArticleAsk(event: Event) {
      const detail = (event as CustomEvent<{ question?: string; context?: string }>).detail;
      if (!detail?.question) return;
      articleLaunchRef.current = true;
      setOpen(true);
      void ask(detail.question, detail.context || "");
    }
    window.addEventListener("snowy:ask", handleArticleAsk);
    return () => window.removeEventListener("snowy:ask", handleArticleAsk);
  }, [messages]);

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      const container = messagesRef.current;
      if (container) container.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [messages, loading]);

  function submit(event: React.FormEvent) {
    event.preventDefault();
    const nextQuestion = question.trim();
    if (!nextQuestion || loading) return;
    setQuestion("");
    void ask(nextQuestion);
  }

  return (
    <>
      {!open && <button className="snowyLauncher" type="button" style={{ "--snowy-drag-x": `${launcherPosition.x}px`, "--snowy-drag-y": `${launcherPosition.y}px` } as React.CSSProperties} onPointerDown={startLauncherDrag} onPointerMove={moveLauncher} onPointerUp={finishLauncherDrag} onPointerCancel={finishLauncherDrag} onClick={() => { if (!dragRef.current.moved) setOpen(true); }} aria-label={copy.open}><span className="snowyLauncherGlow" /><img src="/assistant/snowy-avatar.png" alt="Snowy" /></button>}
      {open && <button type="button" className="snowyBackdrop" aria-label={copy.close} onClick={() => setOpen(false)} />}
      {open && <aside className="snowyPanel" aria-label={copy.open}>
        <header className="snowyHeader"><div className="snowyIdentity"><img src="/assistant/snowy-avatar.png" alt="Snowy" /><div><strong>Snowy</strong><span>{labName} · Research Assistant</span></div></div><button type="button" className="snowyClose" onClick={() => setOpen(false)} aria-label={copy.collapse}>›</button></header>
        <div className="snowyMessages" ref={messagesRef}>
          {messages.map((message, index) => message.role === "user" ? <div className="snowyUserBubble" key={`${message.role}-${index}`}>{message.content}</div> : <div className="snowyMessageGroup" key={`${message.role}-${index}`}><div className="snowyMessageName">Snowy{index === 0 ? ` · ${copy.today}` : ""}</div><div className={`snowyBubble${message.degraded ? " snowyBubbleDegraded" : ""}`}><p>{message.content}</p>{message.meta && <small>{message.meta}</small>}<small className="snowyProvider">{message.degraded ? copy.fallback : message.provider === "deepseek" ? `${copy.answered}${message.webSearchUsed ? copy.web : copy.labOnly}` : `${copy.assistantAnswered}`}</small></div></div>)}
          {loading && <div className="snowyBubble snowyTyping">{copy.typing} <span>•••</span></div>}
        </div>
        <div className="snowySuggestions">{(suggestions.length ? suggestions : copy.suggestions).slice(0, 3).map((item) => <button type="button" key={item} onClick={() => void ask(item)}>{item}</button>)}</div>
        <form className="snowyComposer" onSubmit={submit}><input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder={copy.placeholder} /><button type="submit" aria-label={copy.send}>→</button></form>
      </aside>}
    </>
  );
}
