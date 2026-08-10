import { Article } from "@/lib/api/types";
import { FeaturedArticle } from "@/components/home/hero/types";
import { MediaService } from "@/domains/article/media";

export function mapArticleToFeatured(a: Article): FeaturedArticle {
  const media = MediaService.resolve(a as any);
  const rawThumbUrl = (a as any).thumbnail_url;
  const validUrl = rawThumbUrl && (rawThumbUrl.startsWith("http://") || rawThumbUrl.startsWith("https://")) ? rawThumbUrl : null;
  return {
    id: String(a.id),
    slug: a.slug,
    title: a.title,
    summary: a.summary || "",
    thumbnail: validUrl || media.url || a.thumbnail_local || (a as any).hero_image || "https://images.unsplash.com/photo-1677442136019-21780efad99a?auto=format&fit=crop&w=1200&q=80",
    thumbnail_url: validUrl || undefined,
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
