import { ContentAnalysis, DailySummary } from "@/types";
import { ContentCard } from "@/components/ContentCard";
import { SentimentChart } from "@/components/SentimentChart";
import { DailySummaryCard } from "@/components/DailySummaryCard";
import { Badge } from "@/components/ui/badge";

async function getContents(): Promise<ContentAnalysis[]> {
  try {
    const res = await fetch("http://127.0.0.1:8000/api/contents", { 
      cache: "no-store",
    });
    if (!res.ok) return [];
    return res.json();
  } catch (e) {
    console.error(e);
    return [];
  }
}

async function getDailySummary(): Promise<DailySummary | null> {
  try {
    const res = await fetch("http://127.0.0.1:8000/api/daily-summary", {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json();
  } catch (e) {
    console.error(e);
    return null;
  }
}

export default async function Home() {
  const [data, summary] = await Promise.all([
    getContents(), // 이름 변경
    getDailySummary()
  ]);

  return (
    <main className="min-h-screen bg-slate-50 p-8 dark:bg-slate-950">
      <div className="mx-auto max-w-6xl space-y-8">
        
        {/* 헤더 */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              📈 주식 AI 에이전트
            </h1>
            <p className="text-slate-500 mt-1">
              YouTube 및 Telegram 데이터를 실시간 분석합니다.
            </p>
          </div>
          <Badge variant="outline" className="px-3 py-1">
            Total: {data.length}
          </Badge>
        </div>

        {/* 요약 카드 & 차트 (그대로 유지) */}
        <DailySummaryCard summary={summary} />
        {data.length > 0 && <SentimentChart data={data} />}

        {/* ✅ 콘텐츠 카드 그리드 (ContentCard 사용) */}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {data.map((item) => (
            <ContentCard key={item.id} item={item} />
          ))}
        </div>
        
      </div>
    </main>
  );
}