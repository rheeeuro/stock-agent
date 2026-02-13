"use client"; // 필수: 클릭 이벤트가 있으므로 클라이언트 컴포넌트

import { useEffect, useState } from "react";
import { VideoAnalysis } from "@/types";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from "@/components/ui/dialog";
import { Calendar, Youtube, ExternalLink, Bot } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkBreaks from "remark-breaks";

interface VideoCardProps {
  item: VideoAnalysis;
}

// 카드 본문(헤더/콘텐츠/푸터) — SSR·클라이언트 초기 렌더 시 동일 HTML로 hydration 불일치 방지
function CardBody({ item }: { item: VideoAnalysis }) {
  return (
    <>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between mb-2 gap-2">
          <Badge variant="outline" className="group-hover:bg-slate-100 dark:group-hover:bg-slate-800 shrink-0">
            {item.channel_name}
          </Badge>
          <span className="text-xs text-slate-400 flex items-center gap-1 shrink-0 whitespace-nowrap" suppressHydrationWarning>
            <Calendar size={12} />
            {new Date(item.created_at).toLocaleDateString("ko-KR", { timeZone: "Asia/Seoul" })}
          </span>
        </div>
        <CardTitle className="text-left text-lg leading-snug line-clamp-2 min-h-[3.5rem] group-hover:text-blue-600 transition-colors" title={item.video_title}>
          {item.video_title}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 pb-4">
        <p className="text-sm text-slate-500 line-clamp-3 leading-relaxed">
          {item.analysis_content}
        </p>
      </CardContent>
      <CardFooter className="pt-0 pb-4">
        <Button variant="secondary" className="w-full h-8 text-xs cursor-pointer">
          상세 분석 보기
        </Button>
      </CardFooter>
    </>
  );
}

export function VideoCard({ item }: VideoCardProps) {
  // Radix Dialog는 서버/클라이언트에서 ID가 달라 hydration 오류를 일으킴.
  // 마운트 후에만 Dialog를 렌더링해 초기 HTML을 동일하게 유지.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const card = (
    <Card className="flex flex-col h-full cursor-pointer hover:border-slate-400 transition-all hover:shadow-md group">
      <CardBody item={item} />
    </Card>
  );

  if (!mounted) return card;

  return (
    <Dialog>
      <DialogTrigger asChild>{card}</DialogTrigger>

      {/* 2. 모달 영역 (상세 보기) */}
      <DialogContent className="sm:max-w-2xl max-h-[80vh] overflow-y-auto overflow-x-hidden">
        <DialogHeader>
          <div className="flex items-center gap-2 mb-2">
            <Badge>{item.channel_name}</Badge>
            <span className="text-sm text-slate-500" suppressHydrationWarning>
              {new Date(item.created_at).toLocaleString("ko-KR", { timeZone: "Asia/Seoul", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })}
            </span>
          </div>
          <DialogTitle className="text-left text-xl leading-relaxed break-words">
            {item.video_title}
          </DialogTitle>
          <DialogDescription className="flex items-center gap-2 pt-2">
            <a 
              href={`https://youtu.be/${item.video_id}`} 
              target="_blank" 
              rel="noreferrer"
              className="text-blue-500 hover:underline flex items-center gap-1 text-sm font-medium"
            >
              <Youtube size={16} /> 유튜브 영상 보러가기 <ExternalLink size={12} />
            </a>
          </DialogDescription>
        </DialogHeader>

        <div className="mt-4 p-6 bg-slate-50 dark:bg-slate-900 rounded-lg border overflow-x-hidden">
            <div className="flex items-center gap-2 mb-4 text-indigo-600 font-semibold border-b pb-2">
              <Bot size={20} />
              AI 투자 분석 리포트
            </div>
            
            {/* ✅ 마크다운 렌더링 영역 */}
            {/* prose: 기본 타이포그래피 적용 */}
            {/* dark:prose-invert: 다크모드에서 글자색 반전 */}
            <article className="prose prose-slate dark:prose-invert prose-sm w-full max-w-none break-words overflow-x-hidden">
              <ReactMarkdown 
                components={{
                  // 제목 스타일링
                  h2: ({node, ...props}) => <h2 className="text-xl font-bold mt-8 mb-4 text-slate-900 dark:text-slate-100 border-b border-slate-200 dark:border-slate-700 pb-2 break-words" {...props} />,
                  h3: ({node, ...props}) => <h3 className="text-lg font-semibold mt-6 mb-3 text-slate-800 dark:text-slate-200 break-words" {...props} />,
                  // 문단 스타일링
                  p: ({node, ...props}) => <p className="mb-4 leading-7 text-slate-700 dark:text-slate-300 break-words overflow-wrap-anywhere" {...props} />,
                  // 리스트 스타일링
                  ul: ({node, ...props}) => <ul className="list-disc list-inside mb-4 space-y-2 text-slate-700 dark:text-slate-300 break-words" {...props} />,
                  ol: ({node, ...props}) => <ol className="list-decimal list-inside mb-4 space-y-2 text-slate-700 dark:text-slate-300 break-words" {...props} />,
                  li: ({node, ...props}) => <li className="mb-2 leading-7 ml-4 break-words overflow-wrap-anywhere" {...props} />,
                  // 강조 스타일링
                  strong: ({node, ...props}) => <strong className="font-bold text-slate-900 dark:text-slate-100" {...props} />,
                  em: ({node, ...props}) => <em className="italic text-slate-800 dark:text-slate-200" {...props} />,
                  // 인용구 스타일링
                  blockquote: ({node, ...props}) => <blockquote className="border-l-4 border-blue-500 pl-4 py-2 my-4 bg-blue-50 dark:bg-blue-900/20 italic text-slate-700 dark:text-slate-300 break-words overflow-wrap-anywhere" {...props} />,
                  // 코드 스타일링
                  code: ({node, inline, ...props}: any) => 
                    inline ? (
                      <code className="bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded text-sm font-mono text-slate-800 dark:text-slate-200 break-all" {...props} />
                    ) : (
                      <code className="block bg-slate-100 dark:bg-slate-800 p-4 rounded-lg text-sm font-mono text-slate-800 dark:text-slate-200 overflow-x-auto max-w-full" {...props} />
                    ),
                  pre: ({node, ...props}) => <pre className="bg-slate-100 dark:bg-slate-800 p-4 rounded-lg overflow-x-auto mb-4 max-w-full" {...props} />,
                }} 
                remarkPlugins={[remarkBreaks]}
              >    
                {item.analysis_content.replace(/\\n/g, '\n')}
              </ReactMarkdown>
            </article>
          </div>
        
        <div className="bg-yellow-50 dark:bg-yellow-900/20 p-4 rounded text-sm text-yellow-800 dark:text-yellow-200 mt-2">
          💡 <strong>Tip:</strong> 이 분석은 AI가 생성했습니다. 투자 판단의 참고용으로만 활용하세요.
        </div>
      </DialogContent>
    </Dialog>
  );
}