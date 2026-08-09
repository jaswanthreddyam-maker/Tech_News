import { Article } from "@/lib/api/types";
import { FeaturedArticle } from "@/components/home/hero/types";
import { MediaService } from "@/domains/article/media";

export function mapArticleToFeatured(a: Article): FeaturedArticle {
  const media = MediaService.resolve(a as any);
  return {
    id: String(a.id),
    slug: a.slug,
    title: a.title,
    summary: a.summary || "",
    thumbnail: media.url || a.thumbnail_local || a.thumbnail_url || (a as any).hero_image || "",
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
