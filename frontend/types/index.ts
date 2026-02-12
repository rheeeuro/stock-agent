export interface VideoAnalysis {
  id: number;
  video_id: string;
  channel_name: string;
  video_title: string;
  analysis_content: string;
  sentiment_score?: number;
  created_at: string;
}