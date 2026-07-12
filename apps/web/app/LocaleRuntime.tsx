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
  "企业动态": { en: "Company updates", ja: "企業動向" },
  "高校论文": { en: "University papers", ja: "大学論文" },
  "新增企业动态": { en: "New company updates", ja: "新着企業動向" },
  "新增高校论文": { en: "New university papers", ja: "新着大学論文" },
  "新增专利": { en: "New patents", ja: "新着特許" },
  "新增学术顶会": { en: "New conferences", ja: "新着学会" },
  "其他技术新闻": { en: "Other technology news", ja: "その他の技術ニュース" },
  "本周热点": { en: "This Week’s Radar", ja: "今週の注目情報" },
  "企业路线与量产": { en: "Company roadmaps and production", ja: "企業ロードマップと量産" },
  "论文与研究": { en: "Papers and research", ja: "論文と研究" },
  "专利与技术布局": { en: "Patents and technology strategy", ja: "特許と技術戦略" },
  "会议与议程": { en: "Conferences and agendas", ja: "学会と議題" },
  "技术状态迁移": { en: "Technology state changes", ja: "技術状態の変化" },
  "本周新增": { en: "Added this week", ja: "今週の追加" },
  "本月新增": { en: "Added this month", ja: "今月の追加" },
  "条": { en: "items", ja: "件" },
  "本周还没有这一类的新变化。": { en: "There are no new changes in this category this week.", ja: "今週、このカテゴリに新しい変化はありません。" },
  "本月暂无更早的相关变化。": { en: "There are no earlier related changes this month.", ja: "今月、これより前の関連する変化はありません。" },
  "未识别具体对象": { en: "No specific entity identified", ja: "具体的な対象を特定できません" },
  "原文已收录，等待进一步分析。": { en: "The source has been collected and is awaiting further analysis.", ja: "原文を収集済みです。追加分析を待っています。" },
  "登录后查看": { en: "Sign in to view", ja: "ログインして表示" },
  "关注专题": { en: "Topics", ja: "トピック" },
  "围绕一个问题，持续累积变化、资料和判断。": { en: "Track a question over time with changes, evidence, and analysis.", ja: "ひとつの問いを中心に、変化・資料・判断を継続的に蓄積します。" },
  "打开专题 →": { en: "Open topic →", ja: "トピックを開く →" },
  "公共情报池": { en: "Public Intelligence Pool", ja: "公開インテリジェンスプール" },
  "公共层统一采集、去重、基础分析；各 Lab 在此基础上生成专属解读。": { en: "The public layer collects, deduplicates, and analyzes signals; each Lab creates its own interpretation.", ja: "公開レイヤーで収集・重複排除・基礎分析を行い、各Labが独自の解釈を生成します。" },
  "官方发布、路线图、招聘、合作与产线信号。": { en: "Official releases, roadmaps, hiring, partnerships, and production signals.", ja: "公式発表、ロードマップ、採用、提携、生産ラインのシグナル。" },
  "论文与会议": { en: "Papers and conferences", ja: "論文と学会" },
  "论文、会议议程、作者与研究方向变化。": { en: "Papers, conference agendas, authors, and changes in research directions.", ja: "論文、学会議題、著者、研究分野の変化。" },
  "专利与标准": { en: "Patents and standards", ja: "特許と標準" },
  "专利布局、申请人变化、标准与白皮书。": { en: "Patent portfolios, applicant changes, standards, and white papers.", ja: "特許ポートフォリオ、出願人の変化、標準、ホワイトペーパー。" },
  "关注企业路线、产品信号、合作公告与量产进展。": { en: "Track company roadmaps, product signals, partnership announcements, and production progress.", ja: "企業ロードマップ、製品シグナル、提携発表、量産の進展を追跡します。" },
  "问研究雷达": { en: "Ask Research Radar", ja: "Research Radarに質問" },
  "围绕你关注的专题和企业，直接追问最近发生的变化。": { en: "Ask directly about recent changes in the topics and companies you follow.", ja: "フォローしているトピックや企業について、最近の変化を直接質問できます。" },
  "最近 Glass Core 有什么重大变化？": { en: "What major changes happened to Glass Core recently?", ja: "最近Glass Coreにどんな大きな変化がありましたか？" },
  "Intel 是不是快量产了？": { en: "Is Intel close to mass production?", ja: "Intelは量産間近ですか？" },
  "为什么三星路线不一样？": { en: "Why is Samsung taking a different path?", ja: "なぜSamsungの方針は異なるのですか？" },
  "有哪些值得合作的教授？": { en: "Which professors are worth collaborating with?", ja: "共同研究に適した教授は誰ですか？" },
  "数据来源管理": { en: "Source management", ja: "データソース管理" },
  "来源按 Lab 推荐后启用；系统管理员负责维护全局来源目录。": { en: "Sources are enabled after Lab recommendations; system administrators maintain the global catalog.", ja: "ソースはLabの推薦後に有効化され、システム管理者が全体カタログを管理します。" },
  "还没有启用的数据来源": { en: "No data sources are enabled yet", ja: "有効なデータソースはまだありません" },
  "点击右上角“生成推荐”，按 Lab 选择需要使用的来源。": { en: "Click “Generate recommendations” in the upper right and choose sources for each Lab.", ja: "右上の「推薦を生成」をクリックし、Labごとに使用するソースを選択してください。" },
  "管理数据来源 →": { en: "Manage sources →", ja: "ソースを管理 →" },
  "新闻、论文、会议、专利和 AI 检索来源的接入概览。": { en: "An overview of news, papers, conferences, patents, and AI search sources.", ja: "ニュース、論文、学会、特許、AI検索ソースの接続状況です。" },
  "每日自动运行": { en: "Daily automation", ja: "毎日の自動実行" },
  "按设定时间自动完成检索、分析和 Changes 生成。": { en: "Automatically collect, analyze, and generate Changes at the configured time.", ja: "設定時刻に収集・分析・Changes生成を自動実行します。" },
  "运行时间": { en: "Run time", ja: "実行時刻" },
  "时区": { en: "Time zone", ja: "タイムゾーン" },
  "中国标准时间 · Asia/Shanghai": { en: "China Standard Time · Asia/Shanghai", ja: "中国標準時 · Asia/Shanghai" },
  "日本标准时间 · Asia/Tokyo": { en: "Japan Standard Time · Asia/Tokyo", ja: "日本標準時 · Asia/Tokyo" },
  "协调世界时 · UTC": { en: "Coordinated Universal Time · UTC", ja: "協定世界時 · UTC" },
  "太平洋时间 · America/Los_Angeles": { en: "Pacific Time · America/Los_Angeles", ja: "太平洋時間 · America/Los_Angeles" },
  "保存设置": { en: "Save settings", ja: "設定を保存" },
  "保存中...": { en: "Saving...", ja: "保存中…" },
  "设置已保存": { en: "Settings saved", ja: "設定を保存しました" },
  "保存失败，请检查 API 服务状态。": { en: "Save failed. Check the API service status.", ja: "保存に失敗しました。APIサービスの状態を確認してください。" },
  "已开启": { en: "Enabled", ja: "有効" },
  "已关闭": { en: "Disabled", ja: "無効" },
  "运行记录": { en: "Run history", ja: "実行履歴" },
  "还没有运行记录。": { en: "No runs yet.", ja: "実行履歴はまだありません。" },
  "运行雷达 →": { en: "Run radar →", ja: "レーダーを実行 →" },
  "运行中，请稍候...": { en: "Running, please wait...", ja: "実行中です。お待ちください…" },
  "运行中": { en: "Running", ja: "実行中" },
  "已完成": { en: "Completed", ja: "完了" },
  "部分完成": { en: "Partially completed", ja: "一部完了" },
  "失败": { en: "Failed", ja: "失敗" },
  "准备中": { en: "Preparing", ja: "準備中" },
  "抓取来源": { en: "Collecting sources", ja: "ソースを収集中" },
  "AI 检索": { en: "AI search", ja: "AI検索" },
  "分析资料": { en: "Analyzing documents", ja: "資料を分析中" },
  "正在准备运行任务。": { en: "Preparing the radar run.", ja: "レーダー実行を準備しています。" },
  "当前为规则分析 · 配置 AI Provider 后启用": { en: "Rule-based analysis is active · Configure an AI provider to enable AI analysis", ja: "現在はルール分析です · AI分析を有効にするにはAI Providerを設定してください" },
  "数据来源": { en: "Data sources", ja: "データソース" },
  "篇资料": { en: "documents", ja: "件の資料" },
  "暂无": { en: "None", ja: "なし" },
  "有数据": { en: "Has data", ja: "データあり" },
  "异常": { en: "Error", ja: "エラー" },
  "未配置格式": { en: "Format not configured", ja: "形式未設定" },
  "查看来源地址 ↗": { en: "View source URL ↗", ja: "ソースURLを表示 ↗" },
  "最新发布：": { en: "Latest published: ", ja: "最新公開：" },
  "最近抓取：": { en: "Last fetched: ", ja: "最終取得：" },
  "健康检查：": { en: "Health check: ", ja: "ヘルスチェック：" },
  "测试": { en: "Test", ja: "テスト" },
  "立即抓取": { en: "Fetch now", ja: "今すぐ取得" },
  "启用": { en: "Enable", ja: "有効化" },
  "停用": { en: "Disable", ja: "無効化" },
  "删除": { en: "Delete", ja: "削除" },
  "删除数据来源？": { en: "Delete this data source?", ja: "このデータソースを削除しますか？" },
  "取消": { en: "Cancel", ja: "キャンセル" },
  "确认删除": { en: "Confirm delete", ja: "削除を確認" },
  "删除中...": { en: "Deleting...", ja: "削除中…" },
  "关注对象": { en: "Watch items", ja: "ウォッチ対象" },
  "这些对象会影响本 Lab 的检索范围和相关性判断。": { en: "These items define the Lab’s search scope and relevance judgments.", ja: "これらの対象がLabの検索範囲と関連性判断に影響します。" },
  "名称，例如：Intel、张教授": { en: "Name, e.g. Intel or Professor Zhang", ja: "名前（例：Intel、張教授）" },
  "关注理由（可选）": { en: "Why follow? (optional)", ja: "フォロー理由（任意）" },
  "添加关注": { en: "Add watch item", ja: "ウォッチ対象を追加" },
  "保存中": { en: "Saving", ja: "保存中" },
  "成员": { en: "Members", ja: "メンバー" },
  "Lab 权限": { en: "Lab role", ja: "Lab権限" },
  "Lab 成员权限": { en: "Lab member access", ja: "Labメンバー権限" },
  "邀请 Lab 成员": { en: "Invite Lab members", ja: "Labメンバーを招待" },
  "最近操作": { en: "Recent actions", ja: "最近の操作" },
  "记录本 Lab 的权限和邀请变更。": { en: "Permission and invitation changes for this Lab.", ja: "このLabの権限・招待の変更履歴です。" },
  "还没有权限操作记录。": { en: "No permission actions yet.", ja: "権限操作の記録はまだありません。" },
  "为 Lab 选择数据来源": { en: "Choose sources for a Lab", ja: "Labのデータソースを選択" },
  "每批展示 9 条推荐，选择后可以一次性加入当前 Lab。": { en: "Nine recommendations are shown per batch. Select them to add to the current Lab in one step.", ja: "1回につき9件を表示します。選択すると現在のLabに一括追加できます。" },
  "分析中...": { en: "Analyzing...", ja: "分析中…" },
  "换一批": { en: "Next batch", ja: "次の候補" },
  "生成推荐": { en: "Generate recommendations", ja: "推薦を生成" },
  "加入中...": { en: "Adding...", ja: "追加中…" },
  "关闭": { en: "Close", ja: "閉じる" },
  "推荐来源仍由系统管理员统一维护，Lab 只选择使用范围。": { en: "The system administrator maintains sources; Labs only choose their scope.", ja: "ソースはシステム管理者が管理し、Labは利用範囲のみ選択します。" },
  "使用此来源": { en: "Use this source", ja: "このソースを使う" },
  "已使用": { en: "In use", ja: "使用中" },
  "系统已停用": { en: "Disabled by system", ja: "システムにより無効" },
  "数据源由系统管理员统一维护。": { en: "Sources are maintained centrally by the system administrator.", ja: "ソースはシステム管理者が一元管理します。" },
  "本周有哪些变化值得关注？": { en: "What changes are worth watching this week?", ja: "今週、注目すべき変化は？" },
  "本周判断": { en: "This week’s assessment", ja: "今週の判断" },
  "系统从你关注的企业、教授和学术会议中筛选信号，只把与 ": { en: "The system filters signals from the companies, professors, and conferences you follow, showing only changes relevant to ", ja: "システムはフォロー中の企業・教授・学会からシグナルを抽出し、" },
  " 研究范围相关的变化放到这里。": { en: " research scope.", ja: "の研究範囲に関連する変化だけを表示します。" },
  "暂无相关变化。": { en: "No related changes yet.", ja: "関連する変化はまだありません。" },
  "今天最值得关注的变化": { en: "The most important changes today", ja: "今日最も注目すべき変化" },
  "重点变化": { en: "Key changes", ja: "主な変化" },
  "打印 / 导出 PDF": { en: "Print / Export PDF", ja: "印刷 / PDF書き出し" },
  "暂无可汇总的变化。": { en: "No changes to summarize yet.", ja: "まとめられる変化はまだありません。" },
  "公开来源": { en: "Public source", ja: "公開ソース" },
  "你的 Lab": { en: "Your Lab", ja: "あなたのLab" },
  "已获取全文": { en: "Full text available", ja: "全文取得済み" },
  "已获取摘要": { en: "Abstract available", ja: "要旨取得済み" },
  "仅有元数据": { en: "Metadata only", ja: "メタデータのみ" },
  "让 Snowy 深度分析": { en: "Ask Snowy for deep analysis", ja: "Snowyに深掘り分析を依頼" },
  "打开 Snowy 研究助手": { en: "Open Snowy Research Assistant", ja: "Snowy研究アシスタントを開く" },
  "AI 洞察报告": { en: "AI insight report", ja: "AIインサイトレポート" },
  "查看原文 ↗": { en: "View original ↗", ja: "原文を見る ↗" },
  "正在检索相关资料…": { en: "Searching related sources…", ja: "関連資料を検索中…" },
  "暂时没有检索到相关资料，请先运行一次雷达。": { en: "No related sources found yet. Run the radar first.", ja: "関連資料が見つかりません。まずレーダーを実行してください。" },
  "AI 翻译中...": { en: "Translating with AI...", ja: "AI翻訳中…" },
};

const originalText = new WeakMap<Text, string>();
const originalAttributes = new WeakMap<Element, Map<string, string>>();
const originalLocalizedText = new WeakMap<Element, string>();

function translateValue(value: string, locale: "en" | "ja") {
  const item = translations[value];
  if (item) return item[locale];
  const count = value.match(/^(\d+)\s*条$/);
  if (count) return locale === "ja" ? `${count[1]} 件` : `${count[1]} items`;
  const level = value.match(/^(\S+)级$/);
  if (level) return locale === "ja" ? `${level[1]}級` : `Level ${level[1]}`;
  const author = value.match(/^作者：(.+)$/);
  if (author) return `${locale === "ja" ? "著者：" : "Author: "}${author[1]}`;
  const source = value.match(/^来源：(.+)$/);
  if (source) return `${locale === "ja" ? "ソース：" : "Source: "}${source[1]}`;
  const admin = value.match(/^管理员：(.+)$/);
  if (admin) return `${locale === "ja" ? "管理者：" : "Administrator: "}${admin[1]}`;
  const members = value.match(/^(\d+) 位成员$/);
  if (members) return locale === "ja" ? `${members[1]}人のメンバー` : `${members[1]} members`;
  const enabled = value.match(/^已启用 (\d+) \/ (\d+)$/);
  if (enabled) return locale === "ja" ? `${enabled[1]} / ${enabled[2]} 件を有効化` : `${enabled[1]} / ${enabled[2]} enabled`;
  const recommended = value.match(/^发现 (\d+) 个推荐来源$/);
  if (recommended) return locale === "ja" ? `${recommended[1]}件の推薦ソース` : `${recommended[1]} recommended sources found`;
  const batch = value.match(/^当前显示 (\d+) 条，共 (\d+) 条可选(，可换一批|，已是全部候选)$/);
  if (batch) {
    const suffix = batch[3].includes("可换") ? (locale === "ja" ? "、次の候補を表示できます" : ", next batch available") : (locale === "ja" ? "、すべての候補を表示中" : ", all candidates shown");
    return locale === "ja" ? `${batch[1]}件を表示、${batch[2]}件を選択可能${suffix}` : `${batch[1]} shown, ${batch[2]} available${suffix}`;
  }
  const topicCount = value.match(/^专题 · (\d+) 条今日变化$/);
  if (topicCount) return locale === "ja" ? `トピック · 今日の変化 ${topicCount[1]}件` : `Topic · ${topicCount[1]} changes today`;
  const relatedCount = value.match(/^(\d+) 条今日相关变化$/);
  if (relatedCount) return locale === "ja" ? `今日の関連変化 ${relatedCount[1]}件` : `${relatedCount[1]} related changes today`;
  const weeklySummary = value.match(/^(.+) 本周有 (\d+) 条相关变化，下面会分别说明它为什么相关，以及对当前判断有什么影响。$/);
  if (weeklySummary) {
    return locale === "ja"
      ? `今週、${weeklySummary[1]}には関連する変化が${weeklySummary[2]}件あります。各項目で関連する理由と現在の判断への影響を説明します。`
      : `${weeklySummary[1]} has ${weeklySummary[2]} relevant changes this week. Each one explains why it matters and how it affects the current assessment.`;
  }
  const watchSummary = value.match(/^管理关注对象、成员角色和邀请。数据源由系统管理员统一维护。$/);
  if (watchSummary) {
    return locale === "ja"
      ? "ウォッチ対象、メンバーの役割、招待を管理します。ソースはシステム管理者が一元管理します。"
      : "Manage watch items, member roles, and invitations. Sources are maintained centrally by the system administrator.";
  }
  const reportDate = value.match(/^(.+) · 基于关注对象、公开资料和 Lab 相关性判断生成$/);
  if (reportDate) {
    return locale === "ja"
      ? `${reportDate[1]} · ウォッチ対象、公開資料、Labの関連性判断に基づいて生成`
      : `${reportDate[1]} · Generated from watch items, public sources, and Lab relevance analysis`;
  }
  if (value.includes("基于关注对象、公开资料和 Lab 相关性判断生成")) {
    const date = value.split("基于关注对象、公开资料和 Lab 相关性判断生成")[0].replace(/[·•]\s*$/, "").trim();
    return locale === "ja"
      ? `${date} · ウォッチ対象、公開資料、Labの関連性判断に基づいて生成`
      : `${date} · Generated from watch items, public sources, and Lab relevance analysis`;
  }
  const labScope = value.match(/^系统从你关注的企业、教授和学术会议中筛选信号，只把与 (.+) 研究范围相关的变化放到这里。$/);
  if (labScope) {
    return locale === "ja"
      ? `システムはフォロー中の企業・教授・学会からシグナルを抽出し、${labScope[1]}の研究範囲に関連する変化だけを表示します。`
      : `The system filters signals from the companies, professors, and conferences you follow, showing only changes relevant to ${labScope[1]}'s research scope.`;
  }
  const reportToday = value.match(/^(.+) 今日识别到 (\d+) 条相关变化。信号主要来自 (.+)，建议优先查看高影响变化及其原始来源。$/);
  if (reportToday) {
    return locale === "ja"
      ? `${reportToday[1]} 今日、関連する変化を${reportToday[2]}件特定しました。主なシグナルは${reportToday[3]}からです。影響の大きい変化と原典を優先して確認してください。`
      : `${reportToday[1]} identified ${reportToday[2]} relevant changes today. Signals mainly came from ${reportToday[3]}; review high-impact changes and their original sources first.`;
  }
  const reportEmpty = value.match(/^(.+) 今日没有新的相关变化，建议继续观察本月信号是否形成连续证据。$/);
  if (reportEmpty) {
    return locale === "ja"
      ? `${reportEmpty[1]} 今日、新しい関連変化はありません。今月のシグナルが継続的な証拠になるか引き続き観察してください。`
      : `${reportEmpty[1]} has no new relevant changes today. Continue watching whether this month's signals form a consistent body of evidence.`;
  }
  const settings = value.match(/^(.+) 设置$/);
  if (settings) return `${settings[1]} ${locale === "ja" ? "設定" : "Settings"}`;
  return value;
}

function translateNode(node: Text, locale: "en" | "ja") {
  if (node.parentElement?.closest("[data-no-translate]")) return;
  const source = originalText.get(node) ?? node.nodeValue ?? "";
  originalText.set(node, source);
  const value = source.trim();
  if (!value) return;
  const next = node.nodeValue!.replace(value, translateValue(value, locale));
  if (node.nodeValue !== next) node.nodeValue = next;
}

function translateAttributes(element: Element, locale: "en" | "ja") {
  if (element.closest("[data-no-translate]")) return;
  const attributes = ["placeholder", "aria-label", "title"];
  const originals = originalAttributes.get(element) ?? new Map<string, string>();
  for (const name of attributes) {
    const current = element.getAttribute(name);
    if (current !== null && !originals.has(name)) originals.set(name, current);
    const source = originals.get(name);
    if (source) {
      const next = translateValue(source, locale);
      if (element.getAttribute(name) !== next) element.setAttribute(name, next);
    }
  }
  originalAttributes.set(element, originals);
}

export default function LocaleRuntime() {
  useEffect(() => {
    const apply = () => {
      const locale = window.localStorage.getItem("radar-language") || "zh-CN";
      document.querySelectorAll<HTMLElement>("[data-i18n-en]").forEach((element) => {
        const original = originalLocalizedText.get(element) ?? element.textContent ?? "";
        originalLocalizedText.set(element, original);
        const next = locale === "zh-CN"
          ? element.getAttribute("data-i18n-zh") ?? original
          : element.getAttribute(locale === "ja" ? "data-i18n-ja" : "data-i18n-en") ?? original;
        if (element.textContent !== next) element.textContent = next;
      });
      document.querySelectorAll("body *").forEach((element) => {
        if (locale === "zh-CN") {
          const originals = originalAttributes.get(element);
          originals?.forEach((value, name) => element.setAttribute(name, value));
          element.childNodes.forEach((node) => {
            if (node.nodeType === Node.TEXT_NODE) {
              const source = originalText.get(node as Text);
              if (source !== undefined) node.nodeValue = source;
            }
          });
          return;
        }
        translateAttributes(element, locale === "ja" ? "ja" : "en");
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
