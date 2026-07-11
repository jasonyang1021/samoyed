export default function Admin() {
  return (
    <>
      <h1>平台管理</h1>
      <div className="grid">
        <div className="card">
          <h3>数据源</h3>
          <p>维护企业官网、会议、论文、专利和新闻来源。</p>
        </div>
        <div className="card">
          <h3>Lab Profile</h3>
          <p>配置 Lab 研究方向、关注对象和重点问题。</p>
        </div>
        <div className="card">
          <h3>运行状态</h3>
          <p>查看采集、分析、变化检测和推送任务。</p>
        </div>
      </div>
    </>
  );
}
