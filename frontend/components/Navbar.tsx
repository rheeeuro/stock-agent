"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { BarChart3, Home, Settings, Globe } from "lucide-react";

const NAV_ITEMS = [
  { href: "/", label: "홈", icon: Home },
  { href: "/dashboard", label: "시황 대시보드", icon: BarChart3 },
  { href: "/admin/tickers", label: "관리", icon: Settings },
];

const MARKET_FILTERS = [
  { value: "ALL", label: "전체", icon: Globe, activeClass: "bg-slate-800 text-white dark:bg-slate-100 dark:text-slate-900" },
  { value: "US", label: "🇺🇸 미국장", icon: null, activeClass: "bg-blue-600 text-white" },
  { value: "KR", label: "🇰🇷 한국장", icon: null, activeClass: "bg-red-500 text-white" },
];

export function Navbar() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const currentMarket = searchParams.get("market") || "ALL";

  // 시장 필터가 의미 있는 페이지인지 확인
  const showMarketFilter = pathname === "/" || pathname === "/dashboard";

  function marketHref(market: string) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("market", market);
    // 홈에서 시장 바꾸면 페이지 1로 리셋
    if (pathname === "/") {
      params.set("page", "1");
    }
    return `${pathname}?${params.toString()}`;
  }

  return (
    <nav className="sticky top-0 z-50 border-b border-slate-200 bg-white/80 backdrop-blur-md dark:border-slate-800 dark:bg-slate-950/80">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-8">
        {/* 왼쪽: 로고 + 네비게이션 */}
        <div className="flex items-center gap-4">
          <Link
            href="/"
            className="text-lg font-bold tracking-tight text-slate-900 dark:text-slate-100"
          >
            📈 주식 AI
          </Link>

          <div className="flex items-center gap-1">
            {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
              const isActive =
                href === "/" ? pathname === "/" : pathname.startsWith(href);

              return (
                <Link
                  key={href}
                  href={href === "/" ? `/?market=${currentMarket}&page=1` : `${href}?market=${currentMarket}`}
                  className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-slate-100 text-slate-900 dark:bg-slate-800 dark:text-slate-100"
                      : "text-slate-500 hover:bg-slate-50 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-900 dark:hover:text-slate-300"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span className="hidden sm:inline">{label}</span>
                </Link>
              );
            })}
          </div>
        </div>

        {/* 오른쪽: 시장 필터 */}
        {showMarketFilter && (
          <div className="flex items-center gap-1.5">
            {MARKET_FILTERS.map(({ value, label, icon: Icon, activeClass }) => {
              const isActive = currentMarket === value;
              return (
                <Link
                  key={value}
                  href={marketHref(value)}
                  className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs sm:text-sm font-bold transition-all ${
                    isActive
                      ? `${activeClass} shadow-sm`
                      : "bg-white text-slate-500 border border-slate-200 hover:bg-slate-50 dark:bg-slate-900 dark:border-slate-800 dark:text-slate-400 dark:hover:bg-slate-800"
                  }`}
                >
                  {Icon && <Icon className="h-3.5 w-3.5" />}
                  {label}
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </nav>
  );
}
