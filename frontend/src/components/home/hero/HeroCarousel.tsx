"use client";

import React, { useState, useEffect } from "react";
import { FeaturedArticle } from "./types";
import { HeroCarouselSkeleton } from "./HeroCarouselSkeleton";
import { HeroScene } from "./v2/HeroScene";

interface HeroCarouselProps {
  items: FeaturedArticle[];
  editorPicks: FeaturedArticle[];
  latest: FeaturedArticle[];
  aiInsights: FeaturedArticle[];
}

export function HeroCarousel({
  items,
  editorPicks,
  latest,
  aiInsights,
}: HeroCarouselProps) {
  const [mounted, setMounted] = useState(false);

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
