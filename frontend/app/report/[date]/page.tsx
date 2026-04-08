import { DailySummary, StockReport } from "@/types";
import { DailySummaryCard } from "@/components/DailySummaryCard";
import { apiFetch } from "@/lib/api";
import { Metadata } from "next";
import Link from "next/link";
import {
  ArrowLeft,
  Crown,
  TrendingUp,
  TrendingDown,
  Minus,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

async function getReportByDate(date: string): Promise<DailySummary | null> {
  return apiFetch(`/api/daily-summary/${date}`, null, {
    next: { revalidate: 3600 },
  } as RequestInit);
}

async function getStockReports(date: string): Promise<StockReport[]> {
  return apiFetch(`/api/stock-report/${date}`, [], {
    next: { revalidate: 3600 },
  } as RequestInit);
}

export async function generateMetadata({ params }: { params: { date: string } }): Promise<Metadata> {
  const resolvedParams = await params;
  const report = await getReportByDate(resolvedParams.date);

  if (!report) {
    return { title: "리포트를 찾을 수 없습니다" };
  }

  const title = `[${resolvedParams.date}] AI가 분석한 오늘의 추천 종목: ${report.buy_stock}`;
  const description = `매수 추천: ${report.buy_stock} (${report.buy_reason}) / 매도 추천: ${report.sell_stock}. AI 주식 에이전트의 일일 브리핑을 확인하세요.`;

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      url: `https://stock.rheeeuro.com/report/${resolvedParams.date}`,
      siteName: "주식 AI 에이전트",
      type: "article",
    },
  };
}

const GRADE_STYLE: Record<string, string> = {
  S: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400",
  A: "bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-400",
  B: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400",
  C: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
};

export default async function ReportPage({ params }: { params: { date: string } }) {
    const resolvedParams = await params;
    const date = resolvedParams.date;

    const [report, stockReports] = await Promise.all([
      getReportByDate(date),
      getStockReports(date),
    ]);

    if (!report && stockReports.length === 0) {
        return (
            <div className="min-h-screen flex items-center justify-center p-8">
                <h1 className="text-2xl font-bold">해당 날짜({date})의 리포트가 없습니다.</h1>
            </div>
        );
    }

    return (
        <main className="min-h-screen bg-slate-50 p-4 sm:p-8 dark:bg-slate-950">
            <div className="mx-auto max-w-6xl space-y-6">
                <Link href="/" className="inline-flex items-center text-sm text-slate-500 hover:text-slate-900 dark:hover:text-slate-100">
          <ArrowLeft className="w-4 h-4 mr-1" /> 메인으로 돌아가기
        </Link>

        <h1 className="text-3xl font-bold tracking-tight">
          {date} AI 투자 리포트
        </h1>

        {/* AI 투자 전략 카드 */}
        {report && <DailySummaryCard summary={report} disableLink />}

        {report && (
          <div className="p-6 bg-white dark:bg-slate-900 rounded-lg shadow-sm border border-slate-200 dark:border-slate-800">
             <h2 className="text-xl font-semibold mb-4">AI 코멘트</h2>
             <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
               오늘 수집된 다양한 유튜브 및 텔레그램 데이터를 종합한 결과입니다.
               투자의 참고 자료로만 활용하시기 바랍니다.
             </p>
          </div>
        )}

        {/* 종목 일간 리포트 목록 */}
        {stockReports.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                종목 수급 분석
              </h2>
              <span className="text-sm text-slate-500 bg-slate-100 dark:bg-slate-800 px-2.5 py-0.5 rounded-full">
                {stockReports.length}개 종목
              </span>
            </div>

            <div className="space-y-3">
              {stockReports.map((r) => {
                const isUp = r.change_pct > 0;
                const isDown = r.change_pct < 0;
                const ChangeIcon = isUp ? TrendingUp : isDown ? TrendingDown : Minus;

                return (
                  <Link key={r.stock_code} href={`/report/${date}/${r.stock_code}`}>
                    <Card className="border-slate-200 dark:border-slate-800 hover:border-indigo-300 dark:hover:border-indigo-700 transition-colors cursor-pointer group my-3">
                      <CardContent className="p-4">
                        <div className="flex items-center gap-4">
                          {/* 순위 */}
                          <div className="w-10 h-10 rounded-full bg-indigo-100 dark:bg-indigo-900/40 flex items-center justify-center shrink-0">
                            <span className="text-sm font-bold text-indigo-700 dark:text-indigo-300">
                              {r.rank_no}
                            </span>
                          </div>

                          {/* 종목명 & 섹터 */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-slate-800 dark:text-slate-100 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                                {r.stock_name}
                              </span>
                              <span className="text-xs text-slate-400 font-mono">
                                {r.stock_code}
                              </span>
                              {r.is_leader && (
                                <Crown className="w-4 h-4 text-amber-500" />
                              )}
                            </div>
                            <div className="flex items-center gap-2 mt-0.5">
                              <span className="text-xs text-slate-500">
                                {r.sector}
                              </span>
                              <span className="text-xs text-slate-400">|</span>
                              <span className="text-xs text-slate-500">
                                거래대금{" "}
                                {(r.trading_value / 1e8).toLocaleString("ko-KR", { maximumFractionDigits: 0 })}억
                              </span>
                            </div>
                          </div>

                          {/* 수급등급 */}
                          <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${GRADE_STYLE[r.supply_grade] || GRADE_STYLE.C}`}>
                            {r.supply_grade}
                          </span>

                          {/* 등락 */}
                          <div className="flex items-center gap-1 w-20 justify-end">
                            <ChangeIcon className={`w-4 h-4 ${isUp ? "text-red-500" : isDown ? "text-blue-500" : "text-slate-400"}`} />
                            <span className={`text-sm font-semibold ${isUp ? "text-red-600 dark:text-red-400" : isDown ? "text-blue-600 dark:text-blue-400" : "text-slate-500"}`}>
                              {isUp ? "+" : ""}{r.change_pct.toFixed(1)}%
                            </span>
                          </div>

                          {/* 점수 */}
                          <div className="w-16 text-right">
                            <span className="text-lg font-bold text-indigo-600 dark:text-indigo-400">
                              {r.score.toFixed(0)}
                            </span>
                            <span className="text-xs text-slate-400">점</span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </Link>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}