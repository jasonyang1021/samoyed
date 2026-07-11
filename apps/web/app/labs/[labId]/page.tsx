export default async function LabPage({ params }: { params: Promise<{ labId: string }> }) {
  const { labId } = await params;

  return (
    <>
      <span className="badge">Lab Space</span>
      <h1>{labId} 今日变化</h1>
      <p className="muted">同一条公共信息，按照本 Lab 的重点问题进行解读。</p>
      <div className="grid">
        <div className="card">
          <h3>量产成熟度可能上升一级</h3>
          <p>工程验证信号增强，但客户与可靠性证据仍不足。</p>
        </div>
        <div className="card">
          <h3>日本供应链关联度上升</h3>
          <p>材料、加工和检测环节出现新的合作线索。</p>
        </div>
        <div className="card">
          <h3>需要继续验证</h3>
          <p>重点追踪良率、产线规模、客户认证与设备采购。</p>
        </div>
      </div>
    </>
  );
}
