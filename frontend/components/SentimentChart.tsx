"use client";

import { ContentAnalysis } from "@/types";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface Props {
  data: ContentAnalysis[];
}

export function SentimentChart({ data }: Props) {
  // 1. 차트용 데이터로 가공 (최신순 -> 과거순 정렬 뒤집기 등)
  // 원본 데이터는 최신순(DESC)일 테니, 차트는 왼쪽(과거) -> 오른쪽(현재)로 가야 하므로 reverse()
  const chartData = [...data].reverse().map((item) => ({
    name: item.source_name,
    title: item.title,
    // 날짜 포맷 (MM/DD HH:mm)
    date: new Date(item.created_at).toLocaleDateString("ko-KR", {
      month: "numeric",
      day: "numeric",
      hour: "2-digit",
    }),
    score: item.sentiment_score || 50, // 점수 없으면 50(중립)
  }));

  // 커스텀 툴팁 컴포넌트
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const d = payload[0].payload;
      return (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-3 rounded shadow-lg text-sm">
          <p className="font-bold mb-1">{d.title}</p>
          <p className="text-slate-500 text-xs mb-2">
            {d.name} · {d.date}
          </p>
          <p className={`font-bold ${
            d.score >= 80 ? "text-red-500" : d.score <= 20 ? "text-blue-500" : "text-yellow-500"
          }`}>
            점수: {d.score}점
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <Card className="col-span-1 lg:col-span-3"> {/* 전체 너비 사용 */}
      <CardHeader>
        <CardTitle>📊 AI 시장 감정 분석 (Fear & Greed)</CardTitle>
        <CardDescription>
          최근 분석된 영상들의 시장 긍정/부정 지수 흐름입니다. (0: 공포 ~ 100: 탐욕)
        </CardDescription>
      </CardHeader>
      <CardContent className="pl-0">
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis 
                dataKey="date" 
                tick={{ fontSize: 12 }} 
                tickMargin={10} 
              />
              <YAxis 
                domain={[0, 100]} 
                tick={{ fontSize: 12 }} 
                width={40}
              />
              <Tooltip content={<CustomTooltip />} />
              
              {/* 기준선: 50점 (중립) */}
              <ReferenceLine y={50} stroke="#9ca3af" strokeDasharray="3 3" label="중립" />
              
              {/* 메인 데이터 라인 */}
              <Line
                type="monotone"
                dataKey="score"
                stroke="#6366f1" // Indigo 500
                strokeWidth={3}
                dot={{ r: 4, fill: "#6366f1" }}
                activeDot={{ r: 6 }}
                animationDuration={1500}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}