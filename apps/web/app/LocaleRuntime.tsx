"use client";

import { useEffect } from "react";

const translations: Record<string, { en: string; ja: string }> = {
  "Dashboard": { en: "Dashboard", ja: "ダッシュボード" },
  "My Lab": { en: "My Lab", ja: "マイラボ" },
  "正在关注": { en: "Following", ja: "フォロー中" },
  "今天有哪些变化值得关注？": { en: "What changed today?", ja: "今日、注目すべき変化は？" },
  "今日发生了什么？": { en: "What happened today?", ja: "今日何が起きた？" },
  "今日热点": { en: "Today’s Radar", ja: "今日の注目情報" },
  "今日新增": { en: "Added today", ja: "今日の追加" },
  "本周新增": { en: "Added this week", ja: "今週の追加" },
  "本月新增": { en: "Added this month", ja: "今月の追加" },
  "为什么相关": { en: "Why it matters", ja: "関連する理由" },
  "判断影响": { en: "Impact on the lab", ja: "Labへの影響" },
  "查看 My Lab 判断 →": { en: "View My Lab assessment →", ja: "My Labの判断を見る →" },
  "AI 判断": { en: "AI assessment", ja: "AI評価" },
  "今日判断": { en: "Today’s assessment", ja: "今日の判断" },
  "对": { en: "Reference for", ja: "参考：" },
  "的参考": { en: "", ja: "" },
  "系统语言": { en: "System language", ja: "システム言語" },
  "页面风格": { en: "Appearance", ja: "表示スタイル" },
  "亮色": { en: "Light", ja: "ライト" },
  "深色": { en: "Dark", ja: "ダーク" },
  "管理员控制台": { en: "Admin console", ja: "管理コンソール" },
  "退出登录": { en: "Sign out", ja: "ログアウト" },
  "Lab 用户": { en: "Lab user", ja: "Labユーザー" },
  "系统管理员": { en: "System administrator", ja: "システム管理者" },
  "文章语言": { en: "Article language", ja: "記事の言語" },
  "打开原文 ↗": { en: "Open source ↗", ja: "原文を開く ↗" },
  "来源未提供": { en: "Not provided", ja: "未提供" },
  "处理流程": { en: "Processing flow", ja: "処理フロー" },
  "来源采集": { en: "Source collection", ja: "情報収集" },
  "去重": { en: "Deduplication", ja: "重複排除" },
  "相关性判断": { en: "Relevance check", ja: "関連性判断" },
  "Lab 参考": { en: "Lab reference", ja: "Lab参考" },
  "企业动态": { en: "Company news", ja: "企業ニュース" },
  "高校论文": { en: "University papers", ja: "大学論文" },
  "新增企业新闻": { en: "New company news", ja: "新着企業ニュース" },
  "新增高校论文": { en: "New university papers", ja: "新着大学論文" },
  "新增专利": { en: "New patents", ja: "新着特許" },
  "新增学术顶会": { en: "New conferences", ja: "新着学会" },
  "其他技术信息": { en: "Other technology", ja: "その他の技術情報" },
};

function translateNode(node: Text, locale: "en" | "ja") {
  const value = node.nodeValue?.trim();
  if (!value || node.parentElement?.closest("[data-no-translate]")) return;
  const item = translations[value];
  if (item) node.nodeValue = node.nodeValue!.replace(value, item[locale]);
}

export default function LocaleRuntime() {
  useEffect(() => {
    const apply = () => {
      const locale = window.localStorage.getItem("radar-language") || "zh-CN";
      if (locale === "zh-CN") return;
      document.querySelectorAll("body *").forEach((element) => {
        element.childNodes.forEach((node) => { if (node.nodeType === Node.TEXT_NODE) translateNode(node as Text, locale === "ja" ? "ja" : "en"); });
      });
    };
    apply();
    const observer = new MutationObserver(apply);
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, []);
  return null;
}
