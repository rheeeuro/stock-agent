export interface ContentAnalysis {
  id: number;
  external_id: string;   
  source_name: string;  
  title: string;          
  analysis_content: string;
  sentiment_score?: number;
  platform: 'youtube' | 'telegram' | 'news'; 
  market: 'US' | 'KR' | 'CRYPTO' | "UNKNOWN";
  source_url?: string;    
  created_at: string;
  related_tickers?: string[];
}

export interface DailySummary {
  id: number;
  report_date: string;
  buy_stock: string;
  buy_ticker?: string;
  buy_reason: string;
  sell_stock: string;
  sell_ticker?: string;
  sell_reason: string;
  created_at?: string;
}

export interface PaginatedResponse<T> {
  success: boolean;
  data: T[];
  pagination: {
    current_page: number;
    limit: number;
    total_items: number;
    total_pages: number;
    has_next_page: boolean;
    has_prev_page: boolean;
  } | null;
}