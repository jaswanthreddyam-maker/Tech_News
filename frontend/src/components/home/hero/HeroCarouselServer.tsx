import React from "react";
import { getArticles } from "@/lib/api/articles";
import { mapArticlesToFeatured } from "@/lib/mappers/homepage";
import { HeroCarousel } from "./HeroCarousel";

export async function HeroCarouselServer() {
  let featuredArticlesRaw: any[] = [];
  try {
    // Await the API call server-side. Since the backend latency is fixed,
    // this will take < 100ms.
    const articlesRes = await getArticles({ limit: 12, sort_by: "trending" });
    featuredArticlesRaw = Array.isArray(articlesRes) ? articlesRes : (articlesRes as any)?.data || [];
  } catch (error) {
    console.error("Failed to fetch featured articles on server:", error);
  }

  const featuredArticles = mapArticlesToFeatured(featuredArticlesRaw);
  
  const editorPicks = featuredArticles.slice(1);
  const latest = featuredArticles.slice(1);
  const aiInsights = featuredArticles.slice(1);

  return (
    <HeroCarousel
      items={featuredArticles}
      editorPicks={editorPicks}
      latest={latest}
      aiInsights={aiInsights}
    />
  );
}
