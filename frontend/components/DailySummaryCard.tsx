import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DailySummary } from "@/types";
import { TrendingUp, TrendingDown, Calendar } from "lucide-react";
import { StockPriceBadge } from "./StockPriceBadge";
import Link from "next/link";

interface Props {
  summary: DailySummary | null;
}

export function DailySummaryCard({ summary }: Props) {
  if (!summary) return null;

  return (
    <Card className="border-2 border-slate-200 dark:border-slate-800">
      <CardHeader className="pb-2">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <CardTitle className="flex items-center gap-2 text-xl">
            🤖 오늘의 AI 투자 전략
          </CardTitle>
          <div className="flex items-center text-sm text-slate-500 bg-slate-100 px-3 py-1 rounded-full dark:bg-slate-800 shrink-0 w-fit">
            <Calendar className="w-4 h-4 mr-1" />
            {summary.report_date}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          
          {/* 매수 추천 (Bull) */}
          <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-100 dark:border-green-900">
            <div className="flex items-center gap-2 mb-2 text-green-700 dark:text-green-400 font-bold text-lg">
              <TrendingUp className="w-6 h-6" />
              <span>강력 매수 (Buy)</span>
            </div>
            {summary.buy_ticker ? (
              <Link href={`/stock/${summary.buy_ticker}`} className="flex items-center mb-2 group cursor-pointer">
                <span className="text-xl font-bold text-slate-800 dark:text-slate-100 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors underline decoration-indigo-200 dark:decoration-indigo-900 underline-offset-4">
                  {summary.buy_stock || '종목 없음'}
                </span>
                <StockPriceBadge ticker={summary.buy_ticker} />
              </Link>
            ) : (
              <div className="flex items-center mb-2">
                <span className="text-xl font-bold text-slate-800 dark:text-slate-100">
                  {summary.buy_stock || '종목 없음'}
                </span>
              </div>
            )}
            <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
              {summary.buy_reason}
            </p>
          </div>

          {/* 매도 추천 (Bear) */}
          <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-100 dark:border-red-900">
            <div className="flex items-center gap-2 mb-2 text-red-700 dark:text-red-400 font-bold text-lg">
              <TrendingDown className="w-6 h-6" />
              <span>매도/관망 (Sell)</span>
            </div>
            {summary.sell_ticker ? (
              <Link href={`/stock/${summary.sell_ticker}`} className="flex items-center mb-2 group cursor-pointer">
                <span className="text-xl font-bold text-slate-800 dark:text-slate-100 group-hover:text-rose-600 dark:group-hover:text-rose-400 transition-colors underline decoration-rose-200 dark:decoration-rose-900 underline-offset-4">
                  {summary.sell_stock || '종목 없음'}
                </span>
                <StockPriceBadge ticker={summary.sell_ticker} />
              </Link>
            ) : (
              <div className="flex items-center mb-2">
                <span className="text-xl font-bold text-slate-800 dark:text-slate-100">
                  {summary.sell_stock || '종목 없음'}
                </span>
              </div>
            )}
            <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
              {summary.sell_reason}
            </p>
          </div>

        </div>
      </CardContent>
    </Card>
  );
}