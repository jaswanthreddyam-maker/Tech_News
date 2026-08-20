import { useQuery, useInfiniteQuery } from "@tanstack/react-query";
import { getTrendingArticles, getBreakingNews, getLatestNews, getArticles } from "@/lib/api/articles";

export function useTrending() {
  return useQuery({
    queryKey: ["articles", "trending"],
    queryFn: () => getTrendingArticles(),
    staleTime: 30 * 1000,
    gcTime: 2 * 60 * 1000,
    retry: 2,
  });
}

import { getPersonalizedFeed } from "@/lib/api/articles";

export function usePersonalizedFeed(anonymousId?: string | null) {
  return useQuery({
    queryKey: ["articles", "personalized", anonymousId],
    queryFn: () => getPersonalizedFeed(anonymousId),
    staleTime: 30 * 1000,
    gcTime: 2 * 60 * 1000,
    retry: 2,
    enabled: true, // we fetch it anyway, backend falls back to trending
  });
}

export function useBreaking() {
  return useQuery({
    queryKey: ["articles", "breaking"],
    queryFn: () => getBreakingNews(),
    refetchInterval: 30000,
    staleTime: 15 * 1000,
    gcTime: 2 * 60 * 1000,
    retry: 0,
  });
}

export function useHeroArticle() {
  return useQuery({
    queryKey: ["articles", "hero"],
    queryFn: () => getArticles({ limit: 1 }),
    staleTime: 30 * 1000,
    gcTime: 2 * 60 * 1000,
    retry: 1,
  });
}

export function useAIHighlights() {
  return useQuery({
    queryKey: ["articles", "ai-highlights"],
    queryFn: () => getArticles({ limit: 4, category: "artificial-intelligence" }),
    staleTime: 30 * 1000,
    gcTime: 2 * 60 * 1000,
    retry: 2,
  });
}

export function useLatestInfinite() {
  return useInfiniteQuery({
    queryKey: ["articles", "latest"],
    queryFn: getLatestNews,
    initialPageParam: "",
    getNextPageParam: (lastPage: any) => lastPage?.pagination?.next_cursor || undefined,
    staleTime: 30 * 1000,
    gcTime: 2 * 60 * 1000,
    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });
}

import { getCategoryDesks } from "@/lib/api/articles";

export function useCategoryDesks() {
  return useQuery({
    queryKey: ["articles", "desks"],
    queryFn: () => getCategoryDesks(),
    staleTime: 30 * 1000,
    gcTime: 2 * 60 * 1000,
    retry: 1,
    refetchOnWindowFocus: true,
  });
}

