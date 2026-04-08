import { DailySummary } from "@/types";
import { DailySummaryCard } from "@/components/DailySummaryCard";
import { apiFetch } from "@/lib/api";
import { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

// API 호출 함수
async function getReportByDate(date: string): Promise<DailySummary | null> {
  return apiFetch(`/api/daily-summary/${date}`, null, {
    next: { revalidate: 3600 }, // 1시간 캐싱 (서버 부하 감소)
  } as RequestInit);
}

// 🚀 핵심: 동적 메타데이터 생성 (SEO)
export async function generateMetadata({ params }: { params: { date: string } }): Promise<Metadata> {
  const report = await getReportByDate(params.date);
  
  if (!report) {
    return { title: "리포트를 찾을 수 없습니다" };
  }

  const title = `[${params.date}] AI가 분석한 오늘의 추천 종목: ${report.buy_stock}`;
  const description = `매수 추천: ${report.buy_stock} (${report.buy_reason}) / 매도 추천: ${report.sell_stock}. AI 주식 에이전트의 일일 브리핑을 확인하세요.`;

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      url: `https://stock.rheeeuro.com/report/${params.date}`,
      siteName: "주식 AI 에이전트",
      type: "article",
    },
  };
}

// 페이지 UI 렌더링
export default async function ReportPage({ params }: { params: { date: string } }) {
    const resolvedParams = await params;
    const date = resolvedParams.date;
  
    const report = await getReportByDate(date);

    if (!report) {
        return (
            <div className="min-h-screen flex items-center justify-center p-8">
                <h1 className="text-2xl font-bold">해당 날짜({date})의 리포트가 없습니다. 😢</h1>
            </div>
        );
    }

    return (
        <main className="min-h-screen bg-slate-50 p-8 dark:bg-slate-950">
            <div className="mx-auto max-w-6xl space-y-6">
                <Link href="/" className="inline-flex items-center text-sm text-slate-500 hover:text-slate-900 dark:hover:text-slate-100">
          <ArrowLeft className="w-4 h-4 mr-1" /> 메인으로 돌아가기
        </Link>
        
        <h1 className="text-3xl font-bold tracking-tight mb-8">
          📅 {params.date} AI 투자 리포트
        </h1>

        {/* 기존에 만든 카드를 재사용! */}
        <DailySummaryCard summary={report} disableLink />
        
        <div className="mt-8 p-6 bg-white dark:bg-slate-900 rounded-lg shadow-sm border border-slate-200 dark:border-slate-800">
           <h2 className="text-xl font-semibold mb-4">💡 AI 코멘트</h2>
           <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
             오늘 수집된 다양한 유튜브 및 텔레그램 데이터를 종합한 결과입니다. 
             투자의 참고 자료로만 활용하시기 바랍니다.
           </p>
        </div>
      </div>
    </main>
  );
}