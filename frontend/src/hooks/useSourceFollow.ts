"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";
import { useAppStore } from "@/store/useStore";
import { useAuthGate } from "@/hooks/useAuthGate";
import { FeatureCapability } from "@/lib/auth/features";
import { Article } from "@/lib/api/types";

export interface SourceItem {
  id?: number;
  slug: string;
  name: string;
  category: string;
  description: string | null;
  logo_url: string | null;
  url: string;
  credibility_score: number;
  is_following: boolean;
}

export interface FollowingFeedResponse {
  items: Article[];
  followed_sources_count: number;
  total: number;
}

export function useSourceFollow() {
  const { user } = useAppStore();
  const { requireAuthentication } = useAuthGate();
  const queryClient = useQueryClient();

  // 1. Fetch available sources (authenticated receives true is_following, guest receives false)
  const {
    data: sourcesData,
    isLoading: isSourcesLoading,
    error: sourcesError,
    refetch: refetchSources,
  } = useQuery({
    queryKey: ["sources", user?.id ?? "guest"],
    queryFn: async () => {
      const list = await apiFetch<SourceItem[]>("/sources");
      return list || [];
    },
    staleTime: 60_000,
  });

  const sources: SourceItem[] = (sourcesData || []).map((s) => ({
    ...s,
    is_following: user ? !!s.is_following : false,
  }));

  const followedSources = sources.filter((s) => s.is_following);
  const followedCount = followedSources.length;

  // 2. Fetch Following Feed (only for authenticated users with followed sources)
  const {
    data: feedData,
    isLoading: isFeedLoading,
    error: feedError,
    refetch: refetchFeed,
  } = useQuery({
    queryKey: ["following-feed", user?.id ?? "guest", followedSources.map((s) => s.slug).sort().join(",")],
    queryFn: async (): Promise<FollowingFeedResponse> => {
      if (!user || followedCount === 0) {
        return { items: [], followed_sources_count: 0, total: 0 };
      }
      return await apiFetch<FollowingFeedResponse>("/following/feed");
    },
    staleTime: 30_000,
    enabled: !!user,
  });

  // 3. Toggle Follow Mutation (Strict Authenticated Endpoint)
  const toggleFollowMutation = useMutation({
    mutationFn: async ({
      sourceSlug,
      currentlyFollowing,
    }: {
      sourceSlug: string;
      currentlyFollowing: boolean;
    }) => {
      if (currentlyFollowing) {
        return await apiFetch<{ is_following: boolean }>(
          `/users/me/following/sources/${encodeURIComponent(sourceSlug)}`,
          { method: "DELETE" }
        );
      } else {
        return await apiFetch<{ is_following: boolean }>(
          `/users/me/following/sources/${encodeURIComponent(sourceSlug)}`,
          { method: "POST" }
        );
      }
    },
    onMutate: async ({ sourceSlug, currentlyFollowing }) => {
      // Cancel outgoing refetches so they don't overwrite optimistic update
      await queryClient.cancelQueries({ queryKey: ["sources"] });
      await queryClient.cancelQueries({ queryKey: ["following-feed"] });

      // Snapshot previous sources cache
      const prevSources = queryClient.getQueryData<SourceItem[]>(["sources", user?.id ?? "guest"]);

      // Optimistically update
      if (prevSources) {
        queryClient.setQueryData<SourceItem[]>(
          ["sources", user?.id ?? "guest"],
          prevSources.map((s) =>
            s.slug === sourceSlug ? { ...s, is_following: !currentlyFollowing } : s
          )
        );
      }

      return { prevSources };
    },
    onError: (_err, _variables, context) => {
      // Rollback on network/auth failure
      if (context?.prevSources) {
        queryClient.setQueryData(["sources", user?.id ?? "guest"], context.prevSources);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["sources"] });
      queryClient.invalidateQueries({ queryKey: ["following-feed"] });
    },
  });

  const toggleFollow = async (sourceSlug: string) => {
    if (!requireAuthentication(FeatureCapability.SOURCE_FOLLOWING)) {
      return;
    }
    const currentSource = sources.find((s) => s.slug === sourceSlug);
    const currentlyFollowing = currentSource ? currentSource.is_following : false;

    try {
      await toggleFollowMutation.mutateAsync({ sourceSlug, currentlyFollowing });
    } catch {
      // Handled in onError rollback
    }
  };

  return {
    sources,
    followedSources,
    followedCount,
    isSourcesLoading,
    sourcesError,
    refetchSources,
    feedArticles: feedData?.items || [],
    feedSourcesCount: feedData?.followed_sources_count ?? followedCount,
    isFeedLoading,
    feedError,
    refetchFeed,
    toggleFollow,
    isToggling: toggleFollowMutation.isPending,
  };
}
