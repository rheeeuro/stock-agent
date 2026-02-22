import { ContentAnalysis } from "@/types";
import { ContentCard } from "@/components/ContentCard";
import { StockPriceBadge } from "@/components/StockPriceBadge";
import { SentimentChart } from "@/components/SentimentChart";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

// 특정 종목의 데이터를 백엔드에서 가져오는 함수
async function getTickerContents(ticker: string): Promise<ContentAnalysis[]> {
  try {
    const res = await fetch(`http://127.0.0.1:8000/api/contents/${ticker}`, { cache: "no-store" });
    if (!res.ok) return [];
    return res.json();
  } catch (e) {
    return [];
  }
}

async function getStockNameFromDB(ticker: string): Promise<string> {
  try {
    const res = await fetch(`http://127.0.0.1:8000/api/stock-name/${ticker}`, { cache: "no-store" });
    if (!res.ok) return ticker;
    const data = await res.json();
    return data.name;
  } catch (e) {
    return ticker;
  }
}

export default async function StockDetailPage({ params }: { params: { ticker: string } }) {
  // URL에서 티커 이름(예: NVDA)을 빼옵니다 (대문자로 통일)
  const resolvedParams = await Promise.resolve(params);
  const decodedTicker = decodeURIComponent(resolvedParams.ticker).toUpperCase();
  const [stockName, contents] = await Promise.all([
    getStockNameFromDB(decodedTicker),
    getTickerContents(decodedTicker)
  ]);

  // DB에서 찾은 이름이 영문 티커와 다르면(즉, 한글 이름을 찾았으면) "엔비디아(NVDA)" 형태로 조합
  const displayTitle = stockName !== decodedTicker ? `${stockName}(${decodedTicker})` : decodedTicker;

  return (
    <main className="min-h-screen bg-slate-50 p-8 dark:bg-slate-950">
      <div className="mx-auto max-w-6xl space-y-8">
        
        {/* 상단 헤더 & 뒤로가기 & 주가 뱃지 */}
        <div className="flex items-center gap-4 mb-6">
          <Link href="/" className="p-2 bg-white dark:bg-slate-900 rounded-full shadow hover:bg-slate-100 transition-colors">
            <ArrowLeft className="w-5 h-5 text-slate-600 dark:text-slate-300" />
          </Link>
          <div>
            <h1 className="text-3xl font-bold flex items-center text-slate-900 dark:text-slate-100">
              {displayTitle} 집중 분석
              <StockPriceBadge ticker={decodedTicker} />
            </h1>
            <p className="text-slate-500 mt-1">AI가 수집한 최근 관련 뉴스 및 유튜브 감성 분석</p>
          </div>
        </div>

        {/* 데이터가 있을 경우 차트와 카드 표시 */}
        {contents.length > 0 ? (
          <>
            <SentimentChart data={contents} />
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {contents.map((item) => (
                <ContentCard key={item.id} item={item} />
              ))}
            </div>
          </>
        ) : (
          /* 데이터가 없을 경우 안내 문구 */
          <div className="p-12 text-center bg-white dark:bg-slate-900 rounded-xl shadow-sm text-slate-500 border border-slate-200 dark:border-slate-800">
            아직 <strong>{decodedTicker}</strong>에 대해 AI가 수집한 데이터가 없습니다. <br/>
            (다른 종목을 검색하거나, 데이터 수집을 기다려주세요!)
          </div>
        )}
      </div>
    </main>
  );
}