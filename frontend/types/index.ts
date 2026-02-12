export interface VideoAnalysis {
    id: number;
    video_id: string;
    channel_name: string;
    video_title: string;
    analysis_content: string; // AI가 요약한 3줄 내용
    created_at: string;
  }