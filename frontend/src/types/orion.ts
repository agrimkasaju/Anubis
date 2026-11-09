export type MarketSession = 'Pre-market' | 'Regular' | 'After-hours' | 'Overnight 24H ATS' | string;

export interface PendingJob {
  company: string;
  title: string;
  apply_url: string;
  stage?: 'screen' | 'review' | string;
  resume_pdf?: string;
  cover_letter_pdf?: string;
  combined_pdf?: string;
  [key: string]: unknown;
}

export interface JobPendingResponse {
  pending: boolean;
  job?: PendingJob;
}

export interface PipelineStatus {
  running: boolean;
  status_text: string;
  current_job?: string;
  progress?: string;
  pid?: number;
  timestamp?: number;
}

export interface StockData {
  symbol: string;
  stance: 'BULLISH' | 'BEARISH' | 'NEUTRAL' | 'INVALID';
  price: number | null;
  range: string;
  news_call: string;
  raw_analysis: string;
  chart_url: string;
  market_session?: MarketSession;
  regular_price?: number | null;
  overnight_futures?: string;
  sma_50?: number | null;
  sma_200?: number | null;
  thinking_process?: string;
}

export interface SearchResult {
  query: string;
  result: string;
  error?: string;
}

export interface SystemMeta {
  tailscaleAddr: string;
  remoteLlmHost: string;
  isAuthed: boolean;
}
