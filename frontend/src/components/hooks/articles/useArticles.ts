import { useQuery, useInfiniteQuery } from "@tanstack/react-query";
import { getTrendingArticles, getBreakingNews, getLatestNews, getArticles } from "@/lib/api/articles";

export function useTrending() {
  return useQuery({
    queryKey: ["articles", "trending"],
    queryFn: () => getTrendingArticles(),
    staleTime: 10 * 60 * 1000,
    gcTime: 15 * 60 * 1000,
    retry: 2,
  });
}

import { getPersonalizedFeed } from "@/lib/api/articles";

export function usePersonalizedFeed(anonymousId?: string | null) {
  return useQuery({
    queryKey: ["articles", "personalized", anonymousId],
    queryFn: () => getPersonalizedFeed(anonymousId),
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    retry: 2,
    enabled: true, // we fetch it anyway, backend falls back to trending
  });
}

export function useBreaking() {
  return useQuery({
    queryKey: ["articles", "breaking"],
    queryFn: () => getBreakingNews(),
    refetchInterval: 60000,
    staleTime: 30 * 1000,
    gcTime: 5 * 60 * 1000,
    retry: 0,
  });
}

export function useHeroArticle() {
  return useQuery({
    queryKey: ["articles", "hero"],
    queryFn: () => getArticles({ limit: 1 }),
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    retry: 1,
  });
}

export function useAIHighlights() {
  return useQuery({
    queryKey: ["articles", "ai-highlights"],
    queryFn: () => getArticles({ limit: 4, category: "artificial-intelligence" }),
    staleTime: 10 * 60 * 1000,
    gcTime: 15 * 60 * 1000,
    retry: 2,
  });
}

export function useLatestInfinite() {
  return useInfiniteQuery({
    queryKey: ["articles", "latest"],
    queryFn: getLatestNews,
    initialPageParam: "",
    getNextPageParam: (lastPage: any) => lastPage?.pagination?.next_cursor || undefined,
    staleTime: 60 * 1000,
    gcTime: 5 * 60 * 1000,
    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });
}
