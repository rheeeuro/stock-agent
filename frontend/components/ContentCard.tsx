"use client";

import { useEffect, useState } from "react";
import { ContentAnalysis } from "@/types";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from "@/components/ui/dialog";
import { ExternalLink, Youtube, MessageCircle, TrendingUp, TrendingDown, Minus, Bot } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkBreaks from "remark-breaks";

interface Props {
  item: ContentAnalysis;
}

function CardBody({ item }: { item: ContentAnalysis }) {
  // 점수에 따른 색상 및 아이콘 결정
  const getSentimentColor = (score?: number) => {
    if (score === undefined) return "text-slate-500";
    if (score >= 60) return "text-red-500"; // 탐욕/상승
    if (score <= 40) return "text-blue-500"; // 공포/하락
    return "text-amber-500"; // 중립
  };

  const getSentimentIcon = (score?: number) => {
    if (score === undefined) return <Minus className="w-4 h-4" />;
    if (score >= 60) return <TrendingUp className="w-4 h-4" />;
    if (score <= 40) return <TrendingDown className="w-4 h-4" />;
    return <Minus className="w-4 h-4" />;
  };

  return (
    <>
      {/* 1. 헤더: 플랫폼 아이콘 + 채널명 + 점수 */}
      <CardHeader className="p-4 pb-2 space-y-0">
        <div className="flex justify-between items-start">
          <div className="flex items-center gap-2">
            {item.platform === 'youtube' ? (
              <Badge variant="secondary" className="bg-red-100 text-red-600 dark:bg-red-900/30">
                <Youtube className="w-3 h-3 mr-1" /> YouTube
              </Badge>
            ) : (
              <Badge variant="secondary" className="bg-blue-100 text-blue-600 dark:bg-blue-900/30">
                <MessageCircle className="w-3 h-3 mr-1" /> Telegram
              </Badge>
            )}
            <span className="text-xs text-slate-500 font-medium truncate max-w-[100px]">
              {item.source_name}
            </span>
          </div>
          
          {/* 점수 뱃지 */}
          <div className={`flex items-center gap-1 text-xs font-bold ${getSentimentColor(item.sentiment_score)}`}>
            {getSentimentIcon(item.sentiment_score)}
            <span>{item.sentiment_score ?? '-'}점</span>
          </div>
        </div>
      </CardHeader>

      {/* 2. 본문: 제목 + 내용 */}
      <CardContent className="p-4 pt-2 flex-grow">

        <CardTitle className="text-lg leading-tight mb-2 line-clamp-2 text-left">
          {item.title}
        </CardTitle>
        
        <CardDescription className="line-clamp-4 text-sm text-slate-600 dark:text-slate-400 text-left">
          {/* 마크다운 기호 대충 제거해서 보여주기 */}
          {item.analysis_content.replace(/[#*-]/g, '')}
        </CardDescription>
      </CardContent>

      {/* 3. 푸터: 날짜 + 링크 */}
      <CardFooter className="p-4 pt-0 text-xs text-slate-400 flex justify-between items-center">
        <span>{new Date(item.created_at).toLocaleDateString()}</span>
        
        {/* 모달 트리거이므로 직접 링크 대신 '상세보기' 표시 */}
        <div className="flex items-center gap-1 hover:text-slate-600 dark:hover:text-slate-200 transition-colors">
          상세보기 <ExternalLink className="w-3 h-3" />
        </div>
      </CardFooter>
    </>
  );
}

export function ContentCard({ item }: Props) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const card = (
    <Card className="flex flex-col h-full overflow-hidden hover:shadow-lg transition-shadow border-slate-200 dark:border-slate-800 cursor-pointer group">
      <CardBody item={item} />
    </Card>
  );

  if (!mounted) return card;

  return (
    <Dialog>
      <DialogTrigger asChild>{card}</DialogTrigger>

      <DialogContent className="sm:max-w-2xl max-h-[80vh] overflow-y-auto overflow-x-hidden">
        <DialogHeader>
          <div className="flex lg:flex-row sm:flex-col sm:items-center gap-1 sm:gap-2 mb-2 items-start">
            <div className="flex items-center gap-2">
              {item.platform === 'youtube' ? (
                <Badge variant="secondary" className="bg-red-100 text-red-600">YouTube</Badge>
              ) : (
                <Badge variant="secondary" className="bg-blue-100 text-blue-600">Telegram</Badge>
              )}
              <Badge variant="outline">{item.source_name}</Badge>
            </div>
            <span className="text-sm text-slate-500" suppressHydrationWarning>
               {new Date(item.created_at).toLocaleString("ko-KR", { 
                   year: "numeric", month: "2-digit", day: "2-digit", 
                   hour: "2-digit", minute: "2-digit" 
               })}
            </span>
          </div>
          <DialogTitle className="text-left text-xl leading-relaxed break-words">
            {item.title}
          </DialogTitle>
          <DialogDescription className="flex items-center gap-2 pt-2">
            {item.source_url && (
                <a 
                  href={item.source_url} 
                  target="_blank" 
                  rel="noreferrer"
                  className="text-blue-500 hover:underline flex items-center gap-1 text-sm font-medium"
                >
                  <ExternalLink size={16} /> 원본 보러가기
                </a>
            )}
          </DialogDescription>
        </DialogHeader>

        <div className="mt-4 p-6 bg-slate-50 dark:bg-slate-900 rounded-lg border overflow-x-hidden">
            <div className="flex items-center gap-2 mb-4 text-indigo-600 font-semibold border-b pb-2">
              <Bot size={20} />
              AI 투자 분석 리포트
            </div>
            
            <article className="prose prose-slate dark:prose-invert prose-sm w-full max-w-none break-words overflow-x-hidden">
              <ReactMarkdown 
                components={{
                  h2: ({node, ...props}) => <h2 className="text-xl font-bold mt-8 mb-4 text-slate-900 dark:text-slate-100 border-b border-slate-200 dark:border-slate-700 pb-2 break-words" {...props} />,
                  h3: ({node, ...props}) => <h3 className="text-lg font-semibold mt-6 mb-3 text-slate-800 dark:text-slate-200 break-words" {...props} />,
                  p: ({node, ...props}) => <p className="mb-4 leading-7 text-slate-700 dark:text-slate-300 break-words overflow-wrap-anywhere" {...props} />,
                  ul: ({node, ...props}) => <ul className="list-disc list-inside mb-4 space-y-2 text-slate-700 dark:text-slate-300 break-words" {...props} />,
                  ol: ({node, ...props}) => <ol className="list-decimal list-inside mb-4 space-y-2 text-slate-700 dark:text-slate-300 break-words" {...props} />,
                  li: ({node, ...props}) => <li className="mb-2 leading-7 ml-4 break-words overflow-wrap-anywhere" {...props} />,
                  strong: ({node, ...props}) => <strong className="font-bold text-slate-900 dark:text-slate-100" {...props} />,
                  em: ({node, ...props}) => <em className="italic text-slate-800 dark:text-slate-200" {...props} />,
                  blockquote: ({node, ...props}) => <blockquote className="border-l-4 border-blue-500 pl-4 py-2 my-4 bg-blue-50 dark:bg-blue-900/20 italic text-slate-700 dark:text-slate-300 break-words overflow-wrap-anywhere" {...props} />,
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