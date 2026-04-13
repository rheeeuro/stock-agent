import { DailySummary, StockReport, SectorReport } from "@/types";
import { DailySummaryCard } from "@/components/DailySummaryCard";
import { apiFetch } from "@/lib/api";
import { Metadata } from "next";
import Link from "next/link";
import {
  ArrowLeft,
  Crown,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

async function getReportByDate(date: string): Promise<DailySummary | null> {
  return apiFetch(`/api/daily-summary/${date}`, null, {
    next: { revalidate: 600 },
  } as RequestInit);
}

async function getStockReports(date: string): Promise<StockReport[]> {
  return apiFetch(`/api/stock-report/${date}`, [], {
    next: { revalidate: 600 },
  } as RequestInit);
}

async function getSectorReports(date: string): Promise<SectorReport[]> {
  return apiFetch(`/api/sector-report/${date}`, [], {
    next: { revalidate: 600 },
  } as RequestInit);
}

export async function generateMetadata({ params }: { params: { date: string } }): Promise<Metadata> {
  const resolvedParams = await params;
  const report = await getReportByDate(resolvedParams.date);

  if (!report) {
    return { title: "리포트를 찾을 수 없습니다" };
  }

  const title = `[${resolvedParams.date}] 투자 리포트`;
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

    const [report, stockReports, sectorReports] = await Promise.all([
      getReportByDate(date),
      getStockReports(date),
      getSectorReports(date),
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

        {/* 주도 섹터 */}
        {sectorReports.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                주도 섹터
              </h2>
              <span className="text-sm text-slate-500 bg-slate-100 dark:bg-slate-800 px-2.5 py-0.5 rounded-full">
                TOP {sectorReports.length}
              </span>
              {sectorReports[0]?.created_at && (
                <span className="ml-auto text-xs text-slate-400">
                  {new Date(sectorReports[0].created_at).getHours()}시 {new Date(sectorReports[0].created_at).getMinutes()}분 기준
                </span>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {sectorReports.map((s) => {
                const isUp = s.flu_rt > 0;
                const isDown = s.flu_rt < 0;

                return (
                  <Card key={s.thema_grp_cd} className="border-slate-200 dark:border-slate-800">
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <span className="w-7 h-7 rounded-full bg-violet-100 dark:bg-violet-900/40 flex items-center justify-center text-xs font-bold text-violet-700 dark:text-violet-300">
                            {s.rank_no}
                          </span>
                          <span className="font-bold text-slate-800 dark:text-slate-100">
                            {s.thema_nm}
                          </span>
                          <span className="text-xs text-slate-400">
                            {s.stk_num}종목
                          </span>
                        </div>
                        <div className="flex items-center gap-3 text-sm">
                          <span className={isUp ? "text-red-600 dark:text-red-400 font-semibold" : isDown ? "text-blue-600 dark:text-blue-400 font-semibold" : "text-slate-500"}>
                            {isUp ? "+" : ""}{s.flu_rt.toFixed(2)}%
                          </span>
                          <span className="text-xs text-slate-400">
                            기간수익 <span className={s.dt_prft_rt > 0 ? "text-red-500" : s.dt_prft_rt < 0 ? "text-blue-500" : "text-slate-500"}>
                              {s.dt_prft_rt > 0 ? "+" : ""}{s.dt_prft_rt.toFixed(1)}%
                            </span>
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-1.5 mb-2 text-xs text-slate-500">
                        <span className="text-red-500">{s.rising_stk_num}상승</span>
                        <span>/</span>
                        <span className="text-blue-500">{s.fall_stk_num}하락</span>
                      </div>

                      {/* 구성종목 */}
                      <div className="flex flex-wrap gap-1.5">
                        {s.stocks.slice(0, 6).map((stk) => {
                          const stkUp = parseFloat(stk.flu_rt) > 0;
                          const stkDown = parseFloat(stk.flu_rt) < 0;
                          return (
                            <span
                              key={stk.stk_cd}
                              className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-xs"
                            >
                              <span className="text-slate-700 dark:text-slate-300">{stk.stk_nm}</span>
                              <span className={stkUp ? "text-red-500" : stkDown ? "text-blue-500" : "text-slate-400"}>
                                {stkUp ? "+" : ""}{parseFloat(stk.flu_rt).toFixed(1)}%
                              </span>
                            </span>
                          );
                        })}
                        {s.stocks.length > 6 && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-xs text-slate-400">
                            +{s.stocks.length - 6}
                          </span>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
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
              {stockReports[0]?.created_at && (
                <span className="ml-auto text-xs text-slate-400">
                  {new Date(stockReports[0].created_at).getHours()}시 {new Date(stockReports[0].created_at).getMinutes()}분 기준
                </span>
              )}
            </div>

            <div className="grid grid-cols-2 gap-3">
              {stockReports.map((r) => {
                const isUp = r.change_pct > 0;
                const isDown = r.change_pct < 0;

                return (
                  <Link key={r.stock_code} href={`/report/${date}/${r.stock_code}`}>
                    <Card className="border-slate-200 dark:border-slate-800 hover:border-indigo-300 dark:hover:border-indigo-700 transition-colors cursor-pointer group">
                      <CardContent className="p-3 sm:p-4">
                        {/* 상단: 순위 + 종목명 + 배지 */}
                        <div className="flex items-center gap-2 mb-2">
                          <span className="w-6 h-6 sm:w-7 sm:h-7 rounded-full bg-indigo-100 dark:bg-indigo-900/40 flex items-center justify-center text-xs font-bold text-indigo-700 dark:text-indigo-300 shrink-0">
                            {r.rank_no}
                          </span>
                          <span className="font-bold text-sm sm:text-base text-slate-800 dark:text-slate-100 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors truncate">
                            {r.stock_name}
                          </span>
                          {r.is_leader && (
                            <Crown className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                          )}
                          {r.is_theme_stock && (
                            <span className="text-[10px] font-bold text-orange-500 bg-orange-50 dark:bg-orange-950 px-1 py-0.5 rounded shrink-0">테마</span>
                          )}
                        </div>

                        {/* 중단: 섹터 + 거래대금 */}
                        <div className="flex items-center gap-1.5 mb-2 text-xs text-slate-500">
                          <span className="truncate">{r.sector}</span>
                          <span className="text-slate-400 shrink-0">|</span>
                          <span className="shrink-0">
                            {(r.trading_value / 1e8).toLocaleString("ko-KR", { maximumFractionDigits: 0 })}억
                          </span>
                        </div>

                        {/* 하단: 수급등급 + 등락 + 점수 */}
                        <div className="flex items-center justify-between">
                          <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${GRADE_STYLE[r.supply_grade] || GRADE_STYLE.C}`}>
                            수급{r.supply_grade}
                          </span>
                          <span className={`text-xs sm:text-sm font-semibold ${isUp ? "text-red-600 dark:text-red-400" : isDown ? "text-blue-600 dark:text-blue-400" : "text-slate-500"}`}>
                            {isUp ? "+" : ""}{r.change_pct.toFixed(1)}%
                          </span>
                          <div className="text-right">
                            <span className="text-sm sm:text-base font-bold text-indigo-600 dark:text-indigo-400">
                              {r.score.toFixed(0)}
                            </span>
                            <span className="text-[10px] sm:text-xs text-slate-400">점</span>
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

        {/* AI 코멘트 */}
        {report && (
          <div className="p-6 bg-white dark:bg-slate-900 rounded-lg shadow-sm border border-slate-200 dark:border-slate-800">
             <h2 className="text-xl font-semibold mb-4">AI 코멘트</h2>
             <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
               오늘 수집된 다양한 유튜브 및 텔레그램 데이터를 종합한 결과입니다.
               투자의 참고 자료로만 활용하시기 바랍니다.
             </p>
          </div>
        )}
      </div>
    </main>
  );
}