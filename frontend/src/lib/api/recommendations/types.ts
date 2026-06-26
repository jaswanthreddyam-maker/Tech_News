import { Article } from "@/lib/api/types";

export interface RecommendationRequest {
  historyIds: number[];
  currentArticleId?: number;
  limit: number;
  mode?: "history" | "article" | "hybrid";
  userId?: number;
  anonymousId?: string;
}

export interface RecommendationReason {
  type: "similarity" | "trending" | "credible" | "topic" | "freshness";
  score?: number;
  label: "Highly Similar" | "Same Topic" | "Different Perspective" | "Breaking Update" | "Trending" | "Fresh Today" | "Trusted Source" | "Frequently Read Topic" | string;
}

export interface RecommendedArticle extends Article {
  similarity_score?: number;
  reasons?: RecommendationReason[];
  hero_image?: string;
  source_name?: string;
}
