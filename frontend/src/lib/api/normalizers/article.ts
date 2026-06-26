import { RawArticlePayload } from "../schemas/article";

export interface NormalizedArticle extends Omit<RawArticlePayload, "published_at" | "related_articles" | "metadata"> {
  publishedAt: Date | null;
  relatedArticles: Array<{
    id: number;
    title: string;
    slug: string;
    sourceName: string;
    heroImage: string | null;
    publishedAt: Date | null;
  }>;
  whyItMatters: string[];
  timeline: null | any[]; // Explicitly null if not supported, [] if empty
  sourceUrl: string | null;
  sourceName: string | null;
  credibilityScore: number | null;
  metadata: {
    seoTitle: string;
    seoKeywords: string;
    readabilityScore: number;
  };
}

export function normalizeArticle(raw: RawArticlePayload): NormalizedArticle {
  const whyItMatters = raw.metadata?.seo_keywords 
    ? raw.metadata.seo_keywords.split(",").map(k => k.trim()).filter(k => k.length > 0)
    : [];

  let publishedAt: Date | null = null;
  if (raw.published_at) {
    const d = new Date(raw.published_at);
    if (!isNaN(d.getTime())) {
      publishedAt = d;
    }
  }

  const relatedArticles = (raw.related_articles || []).map(r => {
    let rPub: Date | null = null;
    if (r.published_at) {
      const d = new Date(r.published_at);
      if (!isNaN(d.getTime())) {
        rPub = d;
      }
    }
    return {
      id: r.id,
      title: r.title,
      slug: r.slug,
      sourceName: r.source_name || "Unknown",
      heroImage: r.hero_image || null,
      publishedAt: rPub,
    };
  });

  return {
    ...raw,
    hero_image: raw.hero_image || raw.image_url || null,
    publishedAt,
    relatedArticles,
    whyItMatters,
    timeline: null, // Backend does not support timeline yet
    sourceUrl: typeof raw.source === 'string' ? null : (raw.source?.url || null),
    sourceName: typeof raw.source === 'string' ? raw.source : (raw.source?.name || null),
    credibilityScore: typeof raw.source === 'string' ? null : (raw.source?.credibility_score ?? null),
    metadata: {
      seoTitle: raw.metadata?.seo_title || `${raw.title} - Tech News Today`,
      seoKeywords: raw.metadata?.seo_keywords || "",
      readabilityScore: raw.metadata?.readability_score || 0,
    }
  };
}
