export interface SearchScoreComponent {
  component: string;
  score: number;
  weight: number;
  weighted_score: number;
}

export interface SemanticSearchResult {
  type: "article" | "entity" | "topic";
  id: string | number;
  title: string;
  description: string;
  url?: string;
  date?: string;
}

export interface KeywordSearchResult extends SemanticSearchResult {}

export interface SearchFilters {
  category?: string;
  dateRange?: string; // "today", "week", "month"
  source?: string;
  credibility?: number;
  aiConfidence?: number;
  sort?: "relevance" | "freshness";
  matchType?: "all" | "semantic" | "keyword" | "hybrid";
}

export interface SemanticSearchRequest {
  query: string;
  limit?: number;
}
