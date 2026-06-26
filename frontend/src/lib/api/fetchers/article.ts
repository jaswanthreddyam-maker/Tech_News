import { cache } from "react";
import { apiClient } from "../client";
import { normalizeArticle } from "../normalizers/article";
import { thumbnailService } from "../../thumbnails/thumbnailService";

export const getArticle = cache(async (slug: string): Promise<any> => {
  // Fetch via transport layer with tags for ISR
  const payload = await apiClient.fetchJson<any>(`/articles/${slug}`, {
    tags: [`article-${slug}`],
    revalidate: 60,
  });

  if (!payload || !payload.data) {
    return null;
  }

  const rawArticle = {
    ...payload.data.article,
    id: parseInt(payload.data.article.id, 10),
    content: payload.data.content,
    clean_html: payload.data.clean_html,
    hero_image: payload.data.hero_image,
    related_articles: payload.data.related?.articles?.map((a: any) => ({
      id: parseInt(a.id, 10),
      title: a.title,
      slug: a.slug || a.url || "",
      summary: a.summary,
      hero_image: thumbnailService.getPublicImageUrl(a) || null,
      source_name: a.source,
      published_at: a.published_at,
    })) || [],
    metadata: {
      seo_title: payload.data.article.title,
      seo_keywords: "",
      readability_score: 0,
    }
  };

  const normalizedArticle = normalizeArticle(rawArticle);

  return {
    article: normalizedArticle,
    content: payload.data.content,
    clean_html: payload.data.clean_html || payload.data.content,
    related: payload.data.related,
    knowledge: payload.data.knowledge,
    navigation: payload.data.navigation || null,
    images: payload.data.images || null,
    scoring_debug: payload.data.scoring_debug || null,
  };
});
