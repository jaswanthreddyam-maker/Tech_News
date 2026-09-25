"use client";

import React, { useState, useEffect } from "react";
import { FeaturedArticle } from "./types";
import { HeroCarouselSkeleton } from "./HeroCarouselSkeleton";
import { HeroScene } from "./v2/HeroScene";
import { useTrending, useCategoryDesks } from "@/components/hooks/articles/useArticles";
import { mapArticlesToFeatured } from "@/lib/mappers/homepage";
import { MediaService } from "@/domains/article/media";

const SKELETON_ITEMS: FeaturedArticle[] = Array.from({ length: 12 }).map((_, i) => ({
  id: `skeleton-${i}`,
  title: "",
  url: "#",
  thumbnail: "",
} as FeaturedArticle));

interface HeroCarouselProps {
  items?: FeaturedArticle[];
  editorPicks?: FeaturedArticle[];
  latest?: FeaturedArticle[];
  aiInsights?: FeaturedArticle[];
}

export function HeroCarousel({
  items: initialItems = [],
  editorPicks: initialEditorPicks = [],
  latest: initialLatest = [],
  aiInsights: initialAiInsights = [],
}: HeroCarouselProps) {
  const [mounted, setMounted] = useState(false);

  const trendingQuery = useTrending();
  const desksQuery = useCategoryDesks();

  const clientFeatured = React.useMemo(() => {
    const rawClientArticles = Array.isArray(trendingQuery.data)
      ? trendingQuery.data
      : (trendingQuery.data as any)?.data || [];
    return mapArticlesToFeatured(rawClientArticles);
  }, [trendingQuery.data]);

  const deskFeatured = React.useMemo(() => {
    const list: any[] = [];
    if (Array.isArray(desksQuery.data)) {
      for (const desk of desksQuery.data) {
        if (desk && Array.isArray(desk.articles)) {
          list.push(...desk.articles);
        }
      }
    }
    return mapArticlesToFeatured(list);
  }, [desksQuery.data]);

  // Pool all genuine-thumbnailed articles from server items, trending query, and category desks
  const genuinePool = React.useMemo(() => {
    const map = new Map<string, FeaturedArticle>();
    for (const art of [...initialItems, ...clientFeatured, ...deskFeatured]) {
      const artId = String(art.id || art.slug || art.title);
      if (!map.has(artId) && MediaService.hasGenuineThumbnail(art)) {
        map.set(artId, art);
      }
    }
    return Array.from(map.values());
  }, [initialItems, clientFeatured, deskFeatured]);

  // Fallback pool with all unique available articles to prevent false empty states during scraping
  const allPool = React.useMemo(() => {
    const map = new Map<string, FeaturedArticle>();
    for (const art of [...initialItems, ...clientFeatured, ...deskFeatured]) {
      const artId = String(art.id || art.slug || art.title);
      if (!map.has(artId)) {
        map.set(artId, art);
      }
    }
    return Array.from(map.values());
  }, [initialItems, clientFeatured, deskFeatured]);

  // Ensure activePool prioritizes genuine thumbnails, and backfills from allPool to ensure 12 items
  const activePool = React.useMemo(() => {
    const pool: FeaturedArticle[] = [];
    const seen = new Set<string>();

    for (const art of genuinePool) {
      const artId = String(art.id || art.slug || art.title);
      if (!seen.has(artId)) {
        seen.add(artId);
        pool.push(art);
      }
      if (pool.length >= 12) break;
    }

    if (pool.length < 12) {
      for (const art of allPool) {
        const artId = String(art.id || art.slug || art.title);
        if (!seen.has(artId)) {
          seen.add(artId);
          pool.push(art);
        }
        if (pool.length >= 12) break;
      }
    }

    return pool;
  }, [genuinePool, allPool]);

  // If server provided initialItems or activePool has articles, we are NOT loading!
  const hasLoadedArticles = activePool.length > 0 || initialItems.length > 0;
  const isLoading = !hasLoadedArticles && trendingQuery.isLoading;
  const isError = !hasLoadedArticles && trendingQuery.isError && desksQuery.isError;
  const isEmpty = !hasLoadedArticles && !trendingQuery.isLoading;

  const items = React.useMemo(() => {
    if (activePool.length > 0) return activePool.slice(0, 12);
    if (initialItems.length > 0) return initialItems.slice(0, 12);
    return SKELETON_ITEMS;
  }, [activePool, initialItems]);

  const editorPicks = React.useMemo(() => {
    if (initialEditorPicks.length > 0) return initialEditorPicks;
    if (items.length > 1) return items.slice(1, 5);
    return SKELETON_ITEMS.slice(0, 4);
  }, [initialEditorPicks, items]);

  const latest = React.useMemo(() => {
    if (initialLatest.length > 0) return initialLatest;
    if (items.length > 1) return items.slice(1, 5);
    return SKELETON_ITEMS.slice(0, 4);
  }, [initialLatest, items]);

  const aiInsights = React.useMemo(() => {
    if (initialAiInsights.length > 0) return initialAiInsights;
    if (items.length > 1) return items.slice(1, 5);
    return SKELETON_ITEMS.slice(0, 4);
  }, [initialAiInsights, items]);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Render skeleton during SSR / initial hydration so HeroScene mounts fresh on the client,
  // guaranteeing the grand 3D ring arrival animation swoops in from deep space on every visit.
  if (!mounted || isLoading) {
    return <HeroCarouselSkeleton />;
  }

  if (isError) {
    return (
      <div className="w-full h-64 flex flex-col items-center justify-center rounded-xl border border-destructive/20 bg-destructive/5 text-destructive p-6 font-mono text-sm">
        <p className="font-semibold">Failed to load editorial state</p>
        <p className="text-xs text-muted-foreground mt-1">The newsroom API could not be reached or returned an error.</p>
        <button
          onClick={() => trendingQuery.refetch()}
          className="mt-4 px-4 py-2 text-xs rounded-md bg-white/10 hover:bg-white/20 text-white font-mono transition-colors"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  if (isEmpty && !isLoading) {
    return (
      <div className="w-full h-64 flex flex-col items-center justify-center rounded-xl border border-white/10 bg-white/[0.02] text-muted-foreground p-6 font-mono text-sm">
        <p className="font-semibold text-foreground">No stories available right now.</p>
        <p className="text-xs text-muted-foreground mt-1">Autonomous newsroom ingestion is actively discovering emerging tech news.</p>
      </div>
    );
  }

  return (
    <HeroScene
      items={items}
      editorPicks={editorPicks}
      latest={latest}
      aiInsights={aiInsights}
    />
  );
}
