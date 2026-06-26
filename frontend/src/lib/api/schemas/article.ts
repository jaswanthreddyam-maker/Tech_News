import { z } from "zod";

export const SourceInfoSchema = z.object({
  id: z.number().nullable().optional(),
  name: z.string(),
  url: z.string().optional(),
  credibility_score: z.number().optional(),
  reliability_score: z.number().optional(),
  health_state: z.string().optional(),
});

export const RelatedArticleSchema = z.object({
  id: z.number(),
  title: z.string(),
  slug: z.string(),
  summary: z.string().optional(),
  why_this_matters: z.string().nullable().optional(),
  hero_image: z.string().nullable().optional(),
  source_name: z.string().optional(),
  published_at: z.string().optional(),
});

export const ArticleMetadataSchema = z.object({
  seo_title: z.string().optional(),
  seo_keywords: z.string().optional(),
  readability_score: z.number().optional(),
  paragraph_count: z.number().optional(),
  word_count: z.number().optional(),
  response_time_ms: z.number().optional(),
  unique_ratio: z.number().optional(),
});

export const ArticleSchema = z.object({
  id: z.number(),
  title: z.string(),
  slug: z.string(),
  summary: z.string().optional(),
  content: z.string().optional(),
  clean_html: z.string().optional(),
  hero_image: z.string().nullable().optional(),
  image_url: z.string().nullable().optional(),
  thumbnail_url: z.string().nullable().optional(),
  thumbnail_local: z.string().nullable().optional(),
  thumbnail_source: z.string().nullable().optional(),
  thumbnail_quality_score: z.number().nullable().optional(),
  tags: z.array(z.string()).optional(),
  published_at: z.string().nullable().optional(),
  ai_confidence: z.number().optional(),
  reading_time: z.number().optional(),
  category: z.string().optional(),
  source: z.union([z.string(), SourceInfoSchema]).nullable().optional(),
  metadata: ArticleMetadataSchema.nullable().optional(),
  related_articles: z.array(RelatedArticleSchema).nullable().optional(),
});

export type RawArticlePayload = z.infer<typeof ArticleSchema>;
