const changes = [
  { level: "A级变化", title: "Glass Core 工程验证信号增强", why: "从样品展示走向工程验证，量产路径更清晰。", labs: "Glass Core / Advanced Packaging" },
  { level: "B级变化", title: "TGV 可靠性研究出现新的测试组合", why: "多物理场联合验证开始增加。", labs: "Glass Core / Reliability" },
  { level: "弱信号", title: "相关设备岗位与招聘需求上升", why: "可能意味着产线准备活动增强。", labs: "Equipment / Glass Core" },
];

export default function Home() {
  return (
    <>
      <section className="hero">
        <span className="badge">全所变化雷达</span>
        <h1>今天有什么新变化？</h1>
        <p className="muted">不是新闻列表，而是相对过去状态真正发生的变化。</p>
      </section>
      <section className="grid">
        {changes.map((change) => (
          <article className="card" key={change.title}>
            <span className="badge">{change.level}</span>
            <h3>{change.title}</h3>
            <p>{change.why}</p>
            <p className="muted">影响 Lab：{change.labs}</p>
          </article>
        ))}
      </section>
    </>
  );
}
