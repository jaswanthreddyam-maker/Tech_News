import { Article } from "@/lib/api/types";
import { FeaturedArticle } from "@/components/home/hero/types";
import { thumbnailService } from "@/lib/thumbnails/thumbnailService";

export function mapArticleToFeatured(a: Article): FeaturedArticle {
  return {
    id: String(a.id),
    slug: a.slug,
    title: a.title,
    summary: a.summary || "",
    thumbnail: thumbnailService.getPublicImageUrl(a as any),
    source: a.source,
    publishedAt: a.published_at,
    readTime: a.reading_time ?? 3,
    category: a.category
  };
}

export function mapArticlesToFeatured(articles: Article[]): FeaturedArticle[] {
  return articles.map(mapArticleToFeatured);
}
