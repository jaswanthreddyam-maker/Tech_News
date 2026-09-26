import { apiFetch } from "./client";
import { Article, PaginatedResponse, StandardResponse } from "./types";

export async function getArticles(params: {
  category?: string;
  limit?: number;
  cursor?: string;
  sort_by?: string;
}): Promise<PaginatedResponse<Article>> {
  const queryParams: Record<string, string> = {};
  if (params.category) queryParams.category = params.category;
  if (params.limit !== undefined) queryParams.limit = String(params.limit);
  if (params.cursor) queryParams.cursor = params.cursor;
  if (params.sort_by) queryParams.sort_by = params.sort_by;
  return apiFetch<PaginatedResponse<Article>>("/news", { 
    params: queryParams,
    revalidate: 60,
    tags: ["news"],
    timeoutMs: 25000,
  });
}

export async function getArticleById(id: number | string): Promise<StandardResponse<Article>> {
  return apiFetch<StandardResponse<Article>>(`/articles/${id}`);
}

export async function getTrendingArticles(): Promise<PaginatedResponse<Article>> {
  return apiFetch<PaginatedResponse<Article>>("/news", { 
    params: { limit: "25", sort_by: "trending" },
    revalidate: 60,
    tags: ["trending"],
    timeoutMs: 25000,
  });
}

export async function getBreakingNews(): Promise<PaginatedResponse<Article>> {
  return apiFetch<PaginatedResponse<Article>>("/news", { 
    params: { limit: "25", sort_by: "freshness" },
    revalidate: 60,
    tags: ["breaking"],
    timeoutMs: 25000,
  });
}

export async function getPersonalizedFeed(anonymousId?: string | null): Promise<StandardResponse<any[]>> {
  const params: Record<string, string> = { limit: "10" };
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

export async function getCategoryDesks(): Promise<any[]> {
  return apiFetch<any[]>("/news/desks", {
    revalidate: 60,
    tags: ["desks"],
    timeoutMs: 25000,
  });
}


