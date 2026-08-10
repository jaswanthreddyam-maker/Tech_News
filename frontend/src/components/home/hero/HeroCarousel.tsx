"use client";

import React, { useState, useEffect } from "react";
import { FeaturedArticle } from "./types";
import { HeroCarouselSkeleton } from "./HeroCarouselSkeleton";
import { HeroScene } from "./v2/HeroScene";
import { useTrending } from "@/components/hooks/articles/useArticles";
import { mapArticlesToFeatured } from "@/lib/mappers/homepage";

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

  // Client-side fallback fetch if server items were empty
  const trendingQuery = useTrending();
  const rawClientArticles = Array.isArray(trendingQuery.data)
    ? trendingQuery.data
    : (trendingQuery.data as any)?.data || [];

  const clientFeatured = mapArticlesToFeatured(rawClientArticles);
  
  const isLoading = initialItems.length === 0 && trendingQuery.isLoading;
  const isError = initialItems.length === 0 && trendingQuery.isError;
  const isEmpty = initialItems.length === 0 && !trendingQuery.isLoading && clientFeatured.length === 0;

  const skeletonItems = Array.from({ length: 12 }).map((_, i) => ({
    id: `skeleton-${i}`,
    title: "",
    url: "#",
    thumbnail: "",
  } as FeaturedArticle));

  const items = isLoading ? skeletonItems : (initialItems.length > 0 ? initialItems : clientFeatured);
  const editorPicks = isLoading ? skeletonItems.slice(0, 4) : (initialEditorPicks.length > 0 ? initialEditorPicks : clientFeatured.slice(1, 5));
  const latest = isLoading ? skeletonItems.slice(0, 4) : (initialLatest.length > 0 ? initialLatest : clientFeatured.slice(1, 5));
  const aiInsights = isLoading ? skeletonItems.slice(0, 4) : (initialAiInsights.length > 0 ? initialAiInsights : clientFeatured.slice(1, 5));

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    // Avoid hydration mismatch on initial render, but don't block layout
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
