import { getTodayChanges, getMonthlyChanges } from "./lib/api";
import DashboardFeed from "./DashboardFeed";

export const dynamic = "force-dynamic";
const importanceStars: Record<string, string> = { S: "★★★★★", A: "★★★★☆", B: "★★★☆☆", C: "★★☆☆☆" };

export default async function Home() {
  const [changes, monthlyChanges] = await Promise.all([getTodayChanges(), getMonthlyChanges()]);
  return <>
    <DashboardFeed changes={changes} weeklyChanges={monthlyChanges} />
  </>;
}
