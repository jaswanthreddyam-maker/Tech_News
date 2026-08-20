import { Article } from "@/lib/api/types";
import { FeaturedArticle } from "@/components/home/hero/types";
import { MediaService } from "@/domains/article/media";

export function mapArticleToFeatured(a: Article): FeaturedArticle {
  const media = MediaService.resolve(a as any);
  const resolvedImg = media.url || (a as any).thumbnail_url || (a as any).image_url || MediaService.getCategoryFallbackImage(a.category, a.id || a.title);

  return {
    id: String(a.id),
    slug: a.slug,
    title: a.title,
    summary: a.summary || "",
    thumbnail: resolvedImg,
    thumbnail_url: resolvedImg,
    thumbnail_local: a.thumbnail_local || undefined,
    source: a.source,
    publishedAt: a.published_at,
    readTime: a.reading_time ?? 3,
    category: a.category,
    url: a.url,
  };
}

export function mapArticlesToFeatured(articles: Article[]): FeaturedArticle[] {
  return articles.map(mapArticleToFeatured);
}
