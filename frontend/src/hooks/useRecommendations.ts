"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchRecommendations } from "@/lib/api/recommendations/client";
import { usePersonalization } from "@/components/providers/PersonalizationProvider";
import { RecommendedArticle } from "@/lib/api/recommendations/types";

interface UseRecommendationsOptions {
  limit?: number;
  mode?: "history" | "article" | "hybrid";
  currentArticleId?: number;
  enabled?: boolean;
}

export function useRecommendations({ 
  limit = 10, 
  mode = "history", 
  currentArticleId,
  enabled = true 
}: UseRecommendationsOptions = {}) {
  const { readingHistory } = usePersonalization();
  
  const historyIds = readingHistory.map(h => h.articleId);

  // If we are in history mode but have no history, we might disable the query
  // unless we want to fetch trending instead.
  const isQueryEnabled = enabled && (mode !== "history" || historyIds.length > 0 || !!currentArticleId);

  return useQuery<RecommendedArticle[], Error>({
    queryKey: ["recommendations", { mode, limit, currentArticleId, historyHash: historyIds.slice(0, 5).join(",") }],
    queryFn: () => fetchRecommendations({
      historyIds,
      currentArticleId,
      limit,
      mode
    }),
    enabled: isQueryEnabled,
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
  });
}
