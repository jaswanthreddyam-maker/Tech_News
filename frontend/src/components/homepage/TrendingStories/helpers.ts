import { useState, useEffect } from "react";
import { FeedArticle, FeedResponseItem } from "./types";
import { TRENDING_LAYOUT } from "./constants";
import { normalizeCanonicalArticle } from "@/domains/article/normalizer";

/**
 * Extracts and formats category name from article
 */
export function getCategory(article: FeedArticle): string {
  if (typeof article.category === "string" && article.category.trim() !== "") {
    return article.category;
  }
  if (typeof article.category === "object" && article.category?.name) {
    return article.category.name;
  }
  return "Technology";
}

/**
 * Formats reading time display
 */
export function formatReadTime(article: FeedArticle, isCompact = false): string {
  const time = article.read_time || 4;
  return isCompact ? `${time}m` : `${time} min read`;
}

/**
 * Formats source name display
 */
export function getSource(article: FeedArticle): string {
  return article.source || article.source_domain || "Tech News";
}

/**
 * Gets best available image URL from article
 */
export function getImageUrl(article: FeedArticle): string | null {
  return (article as any).image || article.image_url || article.thumbnail_url || null;
}

/**
 * Partitions feed into 1 Featured story and up to MAX_COMPACT tiles
 */
export function partitionFeed(articles: FeedArticle[]): {
  featured: FeedArticle | null;
  compact: FeedArticle[];
} {
  if (!articles || articles.length === 0) {
    return { featured: null, compact: [] };
  }
  return {
    featured: articles[0],
    compact: articles.slice(1, TRENDING_LAYOUT.MAX_COMPACT + 1),
  };
}

/**
 * Normalizes raw API response item into standard FeedArticle via normalizeCanonicalArticle
 */
export function normalizeArticle(item: FeedResponseItem): FeedArticle {
  const rawDto = item.article || item;
  const canonical = normalizeCanonicalArticle({
    ...rawDto,
    reason: item.reason || rawDto.reason,
  });

  return {
    id: Number(canonical.id) || 0,
    title: canonical.title,
    slug: canonical.slug || undefined,
    url: canonical.url || undefined,
    summary: canonical.summary || undefined,
    description: canonical.summary || undefined,
    category: canonical.category || "Technology",
    source: canonical.source || "Tech News",
    source_domain: canonical.source || undefined,
    image_url: canonical.image || undefined,
    thumbnail_url: canonical.image || undefined,
    image: canonical.image || undefined,
    read_time: canonical.readTime || 4,
    reason: canonical.reason || undefined,
  } as FeedArticle;
}

/**
 * Custom hook to manage anonymous user ID safely without UI local storage access
 */
export function useAnonymousId(): string | null {
  const [anonId, setAnonId] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setAnonId(localStorage.getItem("tnt_anon_id"));
    }
  }, []);

  return anonId;
}
