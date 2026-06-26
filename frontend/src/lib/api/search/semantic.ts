import { apiFetch } from "../client";
import { SemanticSearchResult, SearchFilters } from "./types";

export async function fetchSemanticSearch(
  query: string,
  limit: number = 20,
  filters?: SearchFilters
): Promise<SemanticSearchResult[]> {
  const response = await apiFetch<{ data: SemanticSearchResult[] }>("/search/semantic", {
    method: "POST",
    body: JSON.stringify({
      query,
      limit,
      category: filters?.category,
      date_range: filters?.dateRange === "today" ? "24h" : filters?.dateRange,
      min_credibility: filters?.credibility,
      min_confidence: filters?.aiConfidence,
      sort_by: filters?.sort || "relevance",
    }),
  });
  return response.data || [];
}
