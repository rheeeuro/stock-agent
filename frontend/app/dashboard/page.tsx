import { MarketIndices, MarketIndex, DailySummary } from "@/types";
import { MarketIndexCard } from "@/components/MarketIndexCard";
import { apiFetch } from "@/lib/api";
import Link from "next/link";
import {
  Activity,
  TrendingUp,
  TrendingDown,
  BarChart3,
  Globe,
  Landmark,
  Gem,
} from "lucide-react";

export const dynamic = "force-dynamic";

async function getMarketIndices(): Promise<MarketIndices> {
  return apiFetch("/api/market-indices", { US: [], KR: [], COMMODITIES: [] });
}

async function getMarketLeaders(market: string): Promise<MarketIndex[]> {
  return apiFetch(`/api/market-leaders/${market}`, []);
}

async function getDailySummaryList(market: string): Promise<DailySummary[]> {
  return apiFetch(`/api/daily-summary-list?limit=3&market=${market}`, []);
}

export default async function DashboardPage(props: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const params = await props.searchParams;
  const currentMarket = (params?.market as string) || "ALL";

  const showUS = currentMarket === "ALL" || currentMarket === "US";
  const showKR = currentMarket === "ALL" || currentMarket === "KR";

  const [indices, usLeaders, krLeaders, usSummaries, krSummaries] =
    await Promise.all([
      getMarketIndices(),
      showUS ? getMarketLeaders("US") : Promise.resolve([]),
      showKR ? getMarketLeaders("KR") : Promise.resolve([]),
      showUS ? getDailySummaryList("US") : Promise.resolve([]),
      showKR ? getDailySummaryList("KR") : Promise.resolve([]),
    ]);

  return (
    <main className="min-h-screen bg-slate-50 p-4 sm:p-8 dark:bg-slate-950">
      <div className="mx-auto max-w-6xl space-y-8">
        {/* 헤더 */}
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            <BarChart3 className="h-6 w-6 text-indigo-500" />
            시황 대시보드
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            주요 시장 지표와 주도주 현황을 한눈에 확인하세요.
          </p>
        </div>

        {/* 미국 시장 지수 */}
        {showUS && (
          <Section
            icon={<Globe className="h-5 w-5 text-blue-500" />}
            title="🇺🇸 미국 시장"
          >
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
              {indices.US.map((item) => (
                <MarketIndexCard key={item.symbol} item={item} />
              ))}
            </div>
          </Section>
        )}

        {/* 한국 시장 지수 */}
        {showKR && (
          <Section
            icon={<Landmark className="h-5 w-5 text-red-500" />}
            title="🇰🇷 한국 시장"
          >
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              {indices.KR.map((item) => (
                <MarketIndexCard key={item.symbol} item={item} />
              ))}
            </div>
          </Section>
        )}

        {/* 원자재 & 암호화폐 (항상 표시) */}
        <Section
          icon={<Gem className="h-5 w-5 text-amber-500" />}
          title="원자재 / 암호화폐"
        >
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {indices.COMMODITIES.map((item) => (
              <MarketIndexCard key={item.symbol} item={item} />
            ))}
          </div>
        </Section>

        {/* 주도주 */}
        <div className={`grid gap-8 ${showUS && showKR ? "lg:grid-cols-2" : ""}`}>
          {showUS && (
            <Section
              icon={<TrendingUp className="h-5 w-5 text-blue-500" />}
              title="🇺🇸 미국 주도주"
            >
              <div className="space-y-2">
                {usLeaders.map((item) => (
                  <LeaderRow key={item.symbol} item={item} />
                ))}
              </div>
            </Section>
          )}

          {showKR && (
            <Section
              icon={<TrendingUp className="h-5 w-5 text-red-500" />}
              title="🇰🇷 한국 주도주"
            >
              <div className="space-y-2">
                {krLeaders.map((item) => (
                  <LeaderRow key={item.symbol} item={item} />
                ))}
              </div>
            </Section>
          )}
        </div>

        {/* AI 투자 리포트 요약 */}
        <div className={`grid gap-8 ${showUS && showKR ? "lg:grid-cols-2" : ""}`}>
          {showUS && (
            <Section
              icon={<Activity className="h-5 w-5 text-blue-500" />}
              title="🇺🇸 최근 AI 리포트"
            >
              <SummaryList summaries={usSummaries} />
            </Section>
          )}

          {showKR && (
            <Section
              icon={<Activity className="h-5 w-5 text-red-500" />}
              title="🇰🇷 최근 AI 리포트"
            >
              <SummaryList summaries={krSummaries} />
            </Section>
          )}
        </div>
      </div>
    </main>
  );
}

function Section({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <h2 className="mb-4 flex items-center gap-2 text-lg font-bold text-slate-800 dark:text-slate-100">
        {icon}
        {title}
      </h2>
      {children}
    </section>
  );
}

function LeaderRow({ item }: { item: MarketIndex }) {
  if (item.price === null) return null;

  const isUp = (item.change_percent ?? 0) > 0;
  const isDown = (item.change_percent ?? 0) < 0;
  const changeColor = isUp
    ? "text-red-600 dark:text-red-400"
    : isDown
    ? "text-blue-600 dark:text-blue-400"
    : "text-slate-500";

  const Icon = isUp ? TrendingUp : isDown ? TrendingDown : null;

  const isKr =
    item.symbol.endsWith(".KS") || item.symbol.endsWith(".KQ");
  const priceStr = isKr
    ? `₩${item.price.toLocaleString("ko-KR", { maximumFractionDigits: 0 })}`
    : `$${item.price.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  return (
    <Link
      href={`/stock/${item.symbol}`}
      className="flex items-center justify-between rounded-lg border border-slate-100 bg-slate-50 px-4 py-3 transition-colors hover:border-indigo-300 hover:bg-indigo-50/50 dark:border-slate-800 dark:bg-slate-950 dark:hover:border-indigo-700 dark:hover:bg-indigo-950/30"
    >
      <div className="flex items-center gap-3">
        <span className="text-sm font-bold text-slate-800 dark:text-slate-200">
          {item.name}
        </span>
        <span className="text-xs text-slate-400">{item.symbol}</span>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">
          {priceStr}
        </span>
        <span className={`flex items-center gap-1 text-sm font-semibold ${changeColor}`}>
          {Icon && <Icon className="h-3.5 w-3.5" />}
          {isUp ? "+" : ""}
          {item.change_percent?.toFixed(2)}%
        </span>
      </div>
    </Link>
  );
}

function SummaryList({ summaries }: { summaries: DailySummary[] }) {
  if (summaries.length === 0) {
    return (
      <p className="py-4 text-center text-sm text-slate-400">
        리포트가 없습니다.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {summaries.map((s) => (
        <Link
          key={s.id}
          href={`/report/${s.report_date}`}
          className="block rounded-lg border border-slate-100 p-4 transition-colors hover:border-indigo-300 dark:border-slate-800 dark:hover:border-indigo-700"
        >
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">
              {s.report_date}
            </span>
            {s.market && (
              <span
                className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                  s.market === "US"
                    ? "bg-blue-100 text-blue-600 dark:bg-blue-900/40 dark:text-blue-300"
                    : "bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-300"
                }`}
              >
                {s.market}
              </span>
            )}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <span className="text-[10px] font-semibold uppercase text-emerald-500">
                매수
              </span>
              <p className="text-sm font-bold text-slate-800 dark:text-slate-200 line-clamp-1">
                {s.buy_stock}
              </p>
            </div>
            <div>
              <span className="text-[10px] font-semibold uppercase text-rose-500">
                매도
              </span>
              <p className="text-sm font-bold text-slate-800 dark:text-slate-200 line-clamp-1">
                {s.sell_stock}
              </p>
            </div>
          </div>
        </Link>
      ))}
    </div>
  );
}
