import { apiFetch } from "./client";
import { Article, PaginatedResponse, StandardResponse } from "./types";

export async function getArticles(params: {
  category?: string;
  limit?: number;
  cursor?: string;
}): Promise<PaginatedResponse<Article>> {
  return apiFetch<PaginatedResponse<Article>>("/news", { params: params as Record<string, string> });
}

export async function getArticleById(id: number): Promise<StandardResponse<Article>> {
  return apiFetch<StandardResponse<Article>>(`/news/${id}`);
}

export async function getTrendingArticles(): Promise<PaginatedResponse<Article>> {
  return apiFetch<PaginatedResponse<Article>>("/news", { params: { limit: "7", sort_by: "trending" } });
}

export async function getBreakingNews(): Promise<PaginatedResponse<Article>> {
  return apiFetch<PaginatedResponse<Article>>("/news", { params: { limit: "5", sort_by: "freshness" } });
}

export async function getPersonalizedFeed(anonymousId?: string | null): Promise<StandardResponse<any[]>> {
  const params: Record<string, string> = { limit: "7" };
  if (anonymousId) {
    params.anonymous_id = anonymousId;
  }
  return apiFetch<StandardResponse<any[]>>("/recommendations/feed", { params });
}

export async function getLatestNews({ pageParam }: { pageParam?: string }): Promise<PaginatedResponse<Article>> {
  return apiFetch<PaginatedResponse<Article>>("/news", { params: { limit: "15", cursor: pageParam || "" } });
}

export async function getTrends(): Promise<string[]> {
  const response = await apiFetch<{ topic: string; weight: number }[] | string[]>("/news/trends");
  if (Array.isArray(response)) {
    return response.map(item => typeof item === "string" ? item : item.topic);
  }
  return [];
}

