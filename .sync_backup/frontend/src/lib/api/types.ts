export interface PaginationMetadata {
  next_cursor: string | null;
  has_more: boolean;
  limit: number;
}

export interface PaginatedResponse<T> {
  correlation_id: string;
  data: T[];
  pagination: PaginationMetadata;
}

export interface StandardResponse<T> {
  correlation_id: string;
  data: T;
}

export interface Article {
  id: number;
  title: string;
  slug: string;
  summary: string;
  why_this_matters?: string[] | null;
  content: string;
  image_url?: string | null;
  source: string;
  category: string;
  published_at: string;
  thumbnail_url?: string | null;
  thumbnail_local?: string | null;
  thumbnail_source?: string | null;
  thumbnail_quality_score?: number | null;
  impact_score?: number;
  freshness_score?: number;
  engagement_score?: number;
  final_score?: number;
  ai_confidence?: number;
  sentiment?: string;
  cluster_id?: string;
  is_archived?: boolean;
}

export interface SourceHealth {
  logo?: string;
  name: string;
  credibility: number;
  articles_today: number;
  health: string;
  average_freshness: number;
}

export interface SemanticRecommendation {
  id: number;
  title: string;
  slug: string;
  score: number;
  thumbnail_url?: string | null;
  source: string;
}

export interface User {
  id: number;
  email: string;
  name: string;
  role: string;
  preferences?: any;
}
