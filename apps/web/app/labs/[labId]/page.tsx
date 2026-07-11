import { getLabTodayChanges } from "../../lib/api";

export const dynamic = "force-dynamic";

export default async function LabPage({ params }: { params: Promise<{ labId: string }> }) {
  const { labId } = await params;
  const changes = await getLabTodayChanges(labId);
  const labName = labId === "lab-glass-core" ? "Glass Core Lab" : labId;

  return (
    <>
      <span className="badge">Lab Space</span>
      <h1>{labName} 今日变化</h1>
      <p className="muted">同一条公共变化，按照本 Lab 的重点问题进行解读。</p>
      <div className="grid">
        {changes.map((change) => (
          <article className="card" key={change.id}>
            <div className="cardHeader">
              <span className="badge">{change.importance}级变化</span>
              <span className="muted">{change.title}</span>
            </div>
            <h3>{change.change_summary}</h3>
            <div className="factBlock">
              <strong>为什么相关</strong>
              <p>{change.why_relevant}</p>
            </div>
            <div className="factBlock">
              <strong>对当前判断的影响</strong>
              <p>{change.impact}</p>
            </div>
            <div className="factBlock">
              <strong>下一步观察点</strong>
              <ul>
                {change.lab_next_watch_points.map((point) => (
                  <li key={point}>{point}</li>
                ))}
              </ul>
            </div>
          </article>
        ))}
      </div>
    </>
  );
}
