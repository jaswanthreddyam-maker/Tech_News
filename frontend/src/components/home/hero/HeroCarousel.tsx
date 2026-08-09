"use client";

import React, { useState, useEffect } from "react";
import { FeaturedArticle } from "./types";
import { HeroCarouselSkeleton } from "./HeroCarouselSkeleton";
import { HeroScene } from "./v2/HeroScene";
import { useTrending } from "@/components/hooks/articles/useArticles";
import { mapArticlesToFeatured } from "@/lib/mappers/homepage";

interface HeroCarouselProps {
  items: FeaturedArticle[];
  editorPicks: FeaturedArticle[];
  latest: FeaturedArticle[];
  aiInsights: FeaturedArticle[];
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

  const items = initialItems.length > 0 ? initialItems : clientFeatured;
  const editorPicks = initialEditorPicks.length > 0 ? initialEditorPicks : clientFeatured.slice(1);
  const latest = initialLatest.length > 0 ? initialLatest : clientFeatured.slice(1);
  const aiInsights = initialAiInsights.length > 0 ? initialAiInsights : clientFeatured.slice(1);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
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
