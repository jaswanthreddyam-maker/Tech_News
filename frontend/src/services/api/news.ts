import { apiFetch } from "../api";
import { normalizeArticles } from "./normalizers";
import { z } from "zod";

export const ArticleSchema = z.object({
  id: z.number(),
  title: z.string(),
  slug: z.string(),
  summary: z.string(),
  content: z.string(),
  image_url: z.string().nullable().optional(),
  source: z.string(),
  category: z.string(),
  published_at: z.string(),
  thumbnail_url: z.string().nullable().optional(),
  thumbnail_local: z.string().nullable().optional(),
  thumbnail_last_verified_at: z.string().nullable().optional(),
  thumbnail_content_type: z.string().nullable().optional(),
  thumbnail_width: z.number().nullable().optional(),
  thumbnail_height: z.number().nullable().optional(),
  thumbnail_type: z.string().nullable().optional(),
}).passthrough();

export type Article = z.infer<typeof ArticleSchema>;

export async function searchArticles(query: string, sourceCategory: string, sortBy: string, limit: number = 15): Promise<Article[]> {
  const response = await apiFetch<unknown>(
    `/search?q=${encodeURIComponent(query)}&source_category=${encodeURIComponent(sourceCategory)}&sort_by=${encodeURIComponent(sortBy)}&limit=${limit}`
  );
  const normalized = normalizeArticles(response);
  return z.array(ArticleSchema).parse(normalized);
}
