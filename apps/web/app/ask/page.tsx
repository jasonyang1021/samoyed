import Link from "next/link";

const questions = ["最近 Glass Core 有什么重大变化？", "Intel 是不是快量产了？", "为什么三星路线不一样？", "有哪些值得合作的教授？"];
export default function AskPage() { return <><div className="pageIntro"><span className="badge">ASK AI</span><h1>问研究雷达</h1><p className="muted">围绕你关注的专题和企业，直接追问最近发生的变化。</p></div><section className="askPanel"><div className="askInput">最近 Glass Core 有什么重大变化？<span>→</span></div><div className="questionList">{questions.map((question) => <Link href="/labs/lab-glass-core" className="question" key={question}>{question}<span>→</span></Link>)}</div><p className="muted askNote">AI 问答将在自动分析数据积累后开放。当前可先查看 Glass Core 专题。</p></section></>; }
