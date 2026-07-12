"use client";

export default function SnowyArticleButton({ context, label = "让 Snowy 分析这篇文章", compact = false }: { context: string; label?: string; compact?: boolean }) {
  function openSnowy() {
    window.dispatchEvent(new CustomEvent("snowy:ask", {
      detail: {
        question: "请帮我分析这篇文章：它讲了什么、哪些内容与当前 Lab 最相关、有哪些可信结论和待验证点？",
        context,
      },
    }));
  }

  return <button type="button" className={`snowyArticleButton${compact ? " snowyArticleButtonCompact" : ""}`} onClick={openSnowy}>🐾 {label}</button>;
}
