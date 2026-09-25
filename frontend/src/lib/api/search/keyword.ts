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
    if (filters.category && filters.category !== "all") params.tag = filters.category;
    if (filters.source && filters.source !== "all") params.source_category = filters.source;
    if (filters.sort && filters.sort !== "relevance") params.sort_by = filters.sort;
  }

  const response = await apiFetch<any>("/search", { params });
  if (Array.isArray(response)) {
    return response;
  }
  if (Array.isArray(response?.data)) {
    return response.data;
  }
  return [];
}
