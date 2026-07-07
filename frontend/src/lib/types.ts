export interface MatchedPattern {
  id: string;
  title: string;
  category: string | null;
  similarity_score: number;
}

export interface SessionResponse {
  id: string;
  transcript_text?: string;
  risk_score: number;
  ai_explanation: string;
  matched_patterns: MatchedPattern[] | null;
  status: string;
  created_at: string;
}

export interface MessageResponse {
  id: string;
  role: string;
  content: string;
  created_at: string;
}

export interface SessionDetailResponse extends SessionResponse {
  messages: MessageResponse[];
  entities: any[];
}
