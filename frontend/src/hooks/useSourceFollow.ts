"use client";

import { useState, useEffect, useCallback, useTransition } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";
import { useAppStore } from "@/store/useStore";
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

const LOCAL_STORAGE_KEY = "tnt_followed_sources";

function getLocalFollowedSourceSlugs(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    // Support strings directly and filter out invalid/empty tokens
    return parsed
      .map((item) => (typeof item === "string" ? item.trim() : String(item)))
      .filter((slug) => slug.length > 0 && isNaN(Number(slug)));
  } catch {
    return [];
  }
}

function setLocalFollowedSourceSlugs(slugs: string[]) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(slugs));
  } catch {
    // Ignore localStorage write failures
  }
}

export function useSourceFollow() {
  const { user } = useAppStore();
  const queryClient = useQueryClient();
  const [localFollowedSlugs, setLocalFollowedSlugs] = useState<string[]>([]);
  const [, startTransition] = useTransition();

  // Load guest follows from localStorage on mount
  useEffect(() => {
    setLocalFollowedSlugs(getLocalFollowedSourceSlugs());
  }, []);

  // Sync guest follows into DB upon user login
  useEffect(() => {
    if (!user) return;
    const guestSlugs = getLocalFollowedSourceSlugs();
    if (guestSlugs.length > 0) {
      apiFetch("/users/me/following/sources/sync", {
        method: "POST",
        body: JSON.stringify({ source_slugs: guestSlugs }),
      })
        .then(() => {
          localStorage.removeItem(LOCAL_STORAGE_KEY);
          setLocalFollowedSlugs([]);
          queryClient.invalidateQueries({ queryKey: ["sources"] });
          queryClient.invalidateQueries({ queryKey: ["following-feed"] });
        })
        .catch(() => {
          // Ignore sync network errors on transient drop
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
    const isFollowing = user ? s.is_following : localFollowedSlugs.includes(s.slug);
    return { ...s, is_following: isFollowing };
  });

  const followedSources = sources.filter((s) => s.is_following);
  const followedCount = followedSources.length;

  // Active followed source slugs
  const activeFollowedSlugs = user
    ? followedSources.map((s) => s.slug)
    : localFollowedSlugs;

  // 2. Fetch Following Feed
  const {
    data: feedData,
    isLoading: isFeedLoading,
    error: feedError,
    refetch: refetchFeed,
  } = useQuery({
    queryKey: ["following-feed", user?.id ?? "guest", activeFollowedSlugs.sort().join(",")],
    queryFn: async (): Promise<FollowingFeedResponse> => {
      if (activeFollowedSlugs.length === 0) {
        return { items: [], followed_sources_count: 0, total: 0 };
      }

      if (user) {
        return await apiFetch<FollowingFeedResponse>("/following/feed");
      } else {
        const queryParams = activeFollowedSlugs
          .map((slug) => `source_slugs=${encodeURIComponent(slug)}`)
          .join("&");
        return await apiFetch<FollowingFeedResponse>(`/following/feed?${queryParams}`);
      }
    },
    staleTime: 30_000,
  });

  // 3. Toggle Follow Mutation with Snapshot Rollback
  const toggleFollowMutation = useMutation({
    mutationFn: async ({
      sourceSlug,
      currentlyFollowing,
    }: {
      sourceSlug: string;
      currentlyFollowing: boolean;
    }) => {
      if (!user) {
        // Guest mode: update localStorage
        const current = getLocalFollowedSourceSlugs();
        const next = currentlyFollowing
          ? current.filter((s) => s !== sourceSlug)
          : [...current, sourceSlug];
        setLocalFollowedSlugs(next);
        setLocalFollowedSourceSlugs(next);
        return { is_following: !currentlyFollowing, source_slug: sourceSlug };
      }

      // Logged-in mode: call authenticated API by slug
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

      // Optimistically update sources cache
      queryClient.setQueryData<SourceItem[]>(["sources", user?.id ?? "guest"], (old) => {
        if (!old) return old;
        return old.map((s) =>
          s.slug === sourceSlug ? { ...s, is_following: !currentlyFollowing } : s
        );
      });

      return { prevSources };
    },
    onError: (_err, _vars, context) => {
      // Restore previous state snapshot on error
      if (context?.prevSources) {
        queryClient.setQueryData(["sources", user?.id ?? "guest"], context.prevSources);
      }
    },
    onSettled: () => {
      startTransition(() => {
        queryClient.invalidateQueries({ queryKey: ["sources"] });
        queryClient.invalidateQueries({ queryKey: ["following-feed"] });
      });
    },
  });

  const toggleFollow = useCallback(
    (sourceSlug: string) => {
      const source = sources.find((s) => s.slug === sourceSlug);
      const currentlyFollowing = source ? source.is_following : false;
      toggleFollowMutation.mutate({ sourceSlug, currentlyFollowing });
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
