"use client";

import { useState, useEffect, useCallback, useTransition } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";
import { useAppStore } from "@/store/useStore";
import { Article } from "@/lib/api/types";

export interface SourceItem {
  id: number;
  name: string;
  slug: string | null;
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

const LOCAL_STORAGE_KEY = "tnt_followed_sources";

function getLocalFollowedSourceIds(): number[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.map(Number).filter((n) => !isNaN(n)) : [];
  } catch {
    return [];
  }
}

function setLocalFollowedSourceIds(ids: number[]) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(ids));
  } catch {
    // Ignore localStorage errors
  }
}

export function useSourceFollow() {
  const { user } = useAppStore();
  const queryClient = useQueryClient();
  const [localFollowedIds, setLocalFollowedIds] = useState<number[]>([]);
  const [, startTransition] = useTransition();

  // Load guest follows from localStorage on mount
  useEffect(() => {
    setLocalFollowedIds(getLocalFollowedSourceIds());
  }, []);

  // Sync guest follows into DB upon user login
  useEffect(() => {
    if (!user) return;
    const guestIds = getLocalFollowedSourceIds();
    if (guestIds.length > 0) {
      apiFetch("/users/me/following/sources/sync", {
        method: "POST",
        body: JSON.stringify({ source_ids: guestIds }),
      })
        .then(() => {
          localStorage.removeItem(LOCAL_STORAGE_KEY);
          setLocalFollowedIds([]);
          queryClient.invalidateQueries({ queryKey: ["sources"] });
          queryClient.invalidateQueries({ queryKey: ["following-feed"] });
        })
        .catch(() => {
          // Ignore sync errors on network drops
        });
    }
  }, [user, queryClient]);

  // 1. Fetch available sources
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

  // Calculate effective is_following per source (DB for logged-in, localStorage for guest)
  const sources: SourceItem[] = (sourcesData || []).map((s) => {
    const isFollowing = user ? s.is_following : localFollowedIds.includes(s.id);
    return { ...s, is_following: isFollowing };
  });

  const followedSources = sources.filter((s) => s.is_following);
  const followedCount = followedSources.length;

  // Active followed source IDs
  const activeFollowedIds = user
    ? followedSources.map((s) => s.id)
    : localFollowedIds;

  // 2. Fetch Following Feed
  const {
    data: feedData,
    isLoading: isFeedLoading,
    error: feedError,
    refetch: refetchFeed,
  } = useQuery({
    queryKey: ["following-feed", user?.id ?? "guest", activeFollowedIds.sort().join(",")],
    queryFn: async (): Promise<FollowingFeedResponse> => {
      if (activeFollowedIds.length === 0) {
        return { items: [], followed_sources_count: 0, total: 0 };
      }

      if (user) {
        return await apiFetch<FollowingFeedResponse>("/following/feed");
      } else {
        const queryParams = activeFollowedIds.map((id) => `source_ids=${id}`).join("&");
        return await apiFetch<FollowingFeedResponse>(`/following/feed?${queryParams}`);
      }
    },
    staleTime: 30_000,
  });

  // 3. Toggle Follow Mutation
  const toggleFollowMutation = useMutation({
    mutationFn: async ({ sourceId, currentlyFollowing }: { sourceId: number; currentlyFollowing: boolean }) => {
      if (!user) {
        // Guest mode: update localStorage
        const current = getLocalFollowedSourceIds();
        const next = currentlyFollowing
          ? current.filter((id) => id !== sourceId)
          : [...current, sourceId];
        setLocalFollowedIds(next);
        setLocalFollowedSourceIds(next);
        return { is_following: !currentlyFollowing, source_id: sourceId };
      }

      // Logged-in mode: call authenticated API
      if (currentlyFollowing) {
        return await apiFetch<{ is_following: boolean }>(`/users/me/following/sources/${sourceId}`, {
          method: "DELETE",
        });
      } else {
        return await apiFetch<{ is_following: boolean }>(`/users/me/following/sources/${sourceId}`, {
          method: "POST",
        });
      }
    },
    onMutate: async ({ sourceId, currentlyFollowing }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ["sources"] });
      await queryClient.cancelQueries({ queryKey: ["following-feed"] });

      // Optimistically update sources cache
      queryClient.setQueryData(["sources", user?.id ?? "guest"], (old: SourceItem[] | undefined) => {
        if (!old) return old;
        return old.map((s) => (s.id === sourceId ? { ...s, is_following: !currentlyFollowing } : s));
      });
    },
    onSettled: () => {
      startTransition(() => {
        queryClient.invalidateQueries({ queryKey: ["sources"] });
        queryClient.invalidateQueries({ queryKey: ["following-feed"] });
      });
    },
  });

  const toggleFollow = useCallback(
    (sourceId: number) => {
      const source = sources.find((s) => s.id === sourceId);
      const currentlyFollowing = source ? source.is_following : false;
      toggleFollowMutation.mutate({ sourceId, currentlyFollowing });
    },
    [sources, toggleFollowMutation]
  );

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
