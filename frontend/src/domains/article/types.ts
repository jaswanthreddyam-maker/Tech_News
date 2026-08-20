/**
 * MediaSource — Discriminated origin types for resolved article media assets
 */
export type MediaSource =
  | "hero_image"
  | "thumbnail_local"
  | "thumbnail_url"
  | "image_url"
  | "cover_image"
  | "category_fallback"
  | "fallback";

export interface ResolvedMedia {
  url: string | null;
  source: MediaSource;
}

/**
 * BackendArticleDTO — Raw, un-normalized DTO payload directly from backend REST endpoints
 */
export interface BackendArticleDTO {
  id?: string | number | null;
  slug?: string | null;
  title?: string | null;
  summary?: string | null;
  description?: string | null;
  category?: string | { name?: string } | null;
  source?: string | { name?: string; url?: string } | null;
  source_name?: string | null;
  source_domain?: string | null;
  published_at?: string | null;
  hero_image?: string | null;
  thumbnail_local?: string | null;
  thumbnail_url?: string | null;
  image_url?: string | null;
  cover_image?: string | null;
  thumbnail_status?: string | null;
  read_time?: number | null;
  reading_time?: number | null;
  url?: string | null;
  document_type?: string | null;
  is_multi_topic?: boolean | null;
  primary_topics?: string[] | null;
  dominant_topic_percentage?: number | null;
  reason?: { type: string; message: string } | string | null;
}

/**
 * CanonicalArticle — Frozen, normalized presentation contract consumed by UI components
 */
export interface CanonicalArticle {
  id: string | number;
  slug?: string | null;
  title: string;
  summary?: string | null;
  category?: string | { name?: string } | null;
  image?: string | null;
  imageSource?: MediaSource;
  publishedAt?: string | null;
  source?: string | null;
  url?: string | null;
  readTime?: number | null;
  documentType?: string | null;
  isMultiTopic?: boolean | null;
  primaryTopics?: string[] | null;
  dominantTopicPercentage?: number | null;
  reason?: { type: string; message: string } | string | null;
}
