import { apiFetch } from "../client";
import { KeywordSearchResult, SearchFilters } from "./types";

export async function fetchKeywordSearch(
  query: string,
  filters?: SearchFilters,
  limit: number = 10
): Promise<KeywordSearchResult[]> {
  const params: Record<string, any> = {
    q: query,
    limit,
  };

  if (filters) {
    if (filters.category) params.tag = filters.category;
    if (filters.source) params.source_category = filters.source;
    if (filters.sort) params.sort_by = filters.sort;
  }

  const response = await apiFetch<{ data: KeywordSearchResult[] }>("/search", { params });
  return response.data || [];
}
