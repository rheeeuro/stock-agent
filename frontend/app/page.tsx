import { ContentAnalysis, DailySummary } from "@/types";
import { ContentCard } from "@/components/ContentCard";
import { SentimentChart } from "@/components/SentimentChart";
import { DailySummaryCard } from "@/components/DailySummaryCard";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import { Calendar, ChevronRight } from "lucide-react";

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

async function getDailySummaryList(): Promise<DailySummary[]> {
  try {
    const res = await fetch("http://127.0.0.1:8000/api/daily-summary-list?limit=5", { cache: "no-store" });
    if (!res.ok) return [];
    return res.json();
  } catch (e) {
    return [];
  }
}

export default async function Home() {
  const [data, summary, summaryList] = await Promise.all([
    getContents(),
    getDailySummary(),
    getDailySummaryList()
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

        {summaryList.length > 0 && (
          <div className="mt-12 mb-8 bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold flex items-center gap-2 text-slate-800 dark:text-slate-100">
                <Calendar className="w-5 h-5 text-indigo-500" />
                과거 AI 투자 리포트
              </h2>
            </div>
            
            {/* 리포트 카드 그리드 (가로 정렬) */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {summaryList.map((report) => (
                <Link key={report.id} href={`/report/${report.report_date}`}>
                  <div className="group p-4 border border-slate-100 dark:border-slate-800 rounded-lg hover:border-indigo-500 hover:shadow-md transition-all cursor-pointer bg-slate-50 dark:bg-slate-950 flex flex-col h-full relative overflow-hidden">
                    <span className="text-xs text-slate-400 font-medium mb-1 flex items-center justify-between">
                      {report.report_date}
                      <ChevronRight className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity text-indigo-500" />
                    </span>
                    <span className="font-bold text-slate-700 dark:text-slate-200 text-sm line-clamp-1">
                      {report.buy_stock || '추천 종목'}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        )}

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