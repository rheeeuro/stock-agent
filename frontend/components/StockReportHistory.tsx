import { StockReport } from "@/types";
import { Card, CardContent } from "@/components/ui/card";
import Link from "next/link";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Crown,
  FileBarChart,
} from "lucide-react";

const GRADE_STYLE: Record<string, string> = {
  S: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400",
  A: "bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-400",
  B: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400",
  C: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
  D: "bg-slate-50 text-slate-500 dark:bg-slate-900 dark:text-slate-500",
};

export function StockReportHistory({ reports }: { reports: StockReport[] }) {
  if (reports.length === 0) return null;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <FileBarChart className="w-5 h-5 text-indigo-500" />
        <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">
          최근 일간 리포트
        </h2>
        <span className="text-sm text-slate-500 bg-slate-100 dark:bg-slate-800 px-2.5 py-0.5 rounded-full">
          최근 {reports.length}일
        </span>
      </div>

      <div className="space-y-3">
        {reports.map((r) => {
          const isUp = r.change_pct > 0;
          const isDown = r.change_pct < 0;
          const ChangeIcon = isUp ? TrendingUp : isDown ? TrendingDown : Minus;

          return (
            <Link
              key={r.report_date}
              href={`/report/${r.report_date}/${r.stock_code}`}
            >
              <Card className="border-slate-200 dark:border-slate-800 hover:border-indigo-300 dark:hover:border-indigo-700 transition-colors cursor-pointer group my-2">
                <CardContent className="p-4">
                  <div className="flex items-center gap-4">
                    {/* 날짜 */}
                    <div className="shrink-0">
                      <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                        {r.report_date}
                      </span>
                    </div>

                    {/* 종목명 & 섹터 */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-800 dark:text-slate-100 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                          {r.stock_name}
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
                          #{r.rank_no}위
                        </span>
                        <span className="text-xs text-slate-400">|</span>
                        <span className="text-xs text-slate-500">
                          거래대금{" "}
                          {(r.trading_value / 1e8).toLocaleString("ko-KR", {
                            maximumFractionDigits: 0,
                          })}
                          억
                        </span>
                      </div>
                    </div>

                    {/* 수급등급 + 점수 */}
                    <span
                      className={`px-2.5 py-1 rounded-full text-xs font-bold ${
                        GRADE_STYLE[r.supply_grade] || GRADE_STYLE.D
                      }`}
                    >
                      수급{r.supply_grade} | {r.supply_score?.toFixed(0) ?? 0}
                    </span>

                    {/* 등락 */}
                    <div className="flex items-center gap-1 w-20 justify-end">
                      <ChangeIcon
                        className={`w-4 h-4 ${
                          isUp
                            ? "text-red-500"
                            : isDown
                            ? "text-blue-500"
                            : "text-slate-400"
                        }`}
                      />
                      <span
                        className={`text-sm font-semibold ${
                          isUp
                            ? "text-red-600 dark:text-red-400"
                            : isDown
                            ? "text-blue-600 dark:text-blue-400"
                            : "text-slate-500"
                        }`}
                      >
                        {isUp ? "+" : ""}
                        {r.change_pct.toFixed(1)}%
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
  );
}
