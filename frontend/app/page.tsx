import { Badge } from "@/components/ui/badge";
import { VideoAnalysis } from "@/types";
import { VideoCard } from "@/components/VideoCard";
import { SentimentChart } from "@/components/SentimentChart";


// 데이터 가져오는 함수 (Server Side)
async function getAnalyses(): Promise<VideoAnalysis[]> {
  try {
    // 주의: Next.js 서버(Docker 외부) -> API 서버(Localhost) 호출 시
    // 브라우저가 아니라 '서버'가 호출하므로 http://127.0.0.1:8000 사용
    const res = await fetch("http://127.0.0.1:8000/api/videos?limit=20", {
      cache: "no-store", // 실시간 데이터이므로 캐싱 안 함
    });
    
    if (!res.ok) throw new Error("API 호출 실패");
    return res.json();
  } catch (e) {
    console.error(e);
    return [];
  }
}

export default async function Home() {
  const data = await getAnalyses();

  return (
    <main className="min-h-screen bg-slate-50 p-8 dark:bg-slate-950">
      <div className="mx-auto max-w-6xl space-y-8">
        
        {/* 헤더 */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              📈 주식 AI 에이전트
            </h1>
          </div>
          <Badge variant="outline" className="px-3 py-1">
            Total: {data.length}
          </Badge>
        </div>

        {/* 차트 영역 (데이터가 있을 때만) */}
        {data.length > 0 && (
          <SentimentChart data={data} />
        )}

        {/* 비디오 카드 그리드 */}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {data.map((item) => (
            <VideoCard key={item.id} item={item} />
          ))}
        </div>
        
      </div>
    </main>
  );
}