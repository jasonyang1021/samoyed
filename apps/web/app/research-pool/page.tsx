export default function ResearchPool() {
  return (
    <>
      <h1>公共情报池</h1>
      <p className="muted">公共层统一采集、去重、基础分析；各 Lab 在此基础上生成专属解读。</p>
      <div className="grid">
        <div className="card">
          <h3>企业动态</h3>
          <p>官方发布、路线图、招聘、合作与产线信号。</p>
        </div>
        <div className="card">
          <h3>论文与会议</h3>
          <p>论文、会议议程、作者与研究方向变化。</p>
        </div>
        <div className="card">
          <h3>专利与标准</h3>
          <p>专利布局、申请人变化、标准与白皮书。</p>
        </div>
      </div>
    </>
  );
}
