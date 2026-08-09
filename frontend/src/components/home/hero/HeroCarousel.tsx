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
  /**
   * Pre-fetched server-side items passed from the page Server Component.
   * When provided, skips the client-only !mounted skeleton guard so the LCP
   * <img priority=true> element exists in the SSR HTML — no 10s discovery delay.
   */
  initialItems?: FeaturedArticle[];
}

export function HeroCarousel({
  items: propItems = [],
  editorPicks: initialEditorPicks = [],
  latest: initialLatest = [],
  aiInsights: initialAiInsights = [],
  initialItems = [],
}: HeroCarouselProps) {
  const [mounted, setMounted] = useState(false);

  // Client-side fallback fetch — used when no SSR initialItems are available
  const trendingQuery = useTrending();
  const rawClientArticles = Array.isArray(trendingQuery.data)
    ? trendingQuery.data
    : (trendingQuery.data as any)?.data || [];

  const clientFeatured = mapArticlesToFeatured(rawClientArticles);

  // When the server passes initialItems, use them immediately — no skeleton wait.
  // Without server items, fall back to the client fetch path (skeleton until API resolves).
  const hasServerItems = initialItems.length > 0;

  const isLoading = !hasServerItems && propItems.length === 0 && trendingQuery.isLoading;
  const skeletonItems = Array.from({ length: 12 }).map((_, i) => ({
    id: `skeleton-${i}`,
    title: "",
    url: "#",
    thumbnail: "",
  } as FeaturedArticle));

  const items = isLoading
    ? skeletonItems
    : hasServerItems
    ? initialItems              // SSR path: real articles available immediately
    : propItems.length > 0
    ? propItems
    : clientFeatured;

  const editorPicks = isLoading
    ? skeletonItems.slice(0, 4)
    : initialEditorPicks.length > 0
    ? initialEditorPicks
    : clientFeatured.slice(1, 5);

  const latest = isLoading
    ? skeletonItems.slice(0, 4)
    : initialLatest.length > 0
    ? initialLatest
    : clientFeatured.slice(1, 5);

  const aiInsights = isLoading
    ? skeletonItems.slice(0, 4)
    : initialAiInsights.length > 0
    ? initialAiInsights
    : clientFeatured.slice(1, 5);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Block with skeleton ONLY when there are no server items AND the client hasn't mounted.
  // When initialItems are present, HeroScene renders on the server with real articles,
  // so HeroMediaCard[index=0] renders <Image priority={true}> in the initial HTML.
  if (!mounted && !hasServerItems) {
    return <HeroCarouselSkeleton />;
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
