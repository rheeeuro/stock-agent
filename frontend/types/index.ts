export interface VideoAnalysis {
  id: number;
  video_id: string;
  channel_name: string;
  video_title: string;
  analysis_content: string;
  sentiment_score?: number;
  created_at: string;
}

export interface DailySummary {
  id: number;
  report_date: string;
  buy_stock: string;
  buy_reason: string;
  sell_stock: string;
  sell_reason: string;
}