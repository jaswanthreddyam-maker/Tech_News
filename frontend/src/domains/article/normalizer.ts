import { BackendArticleDTO, CanonicalArticle } from "./types";
import { MediaService } from "./media";

/**
 * normalizeCanonicalArticle — Pure single-entry transformer from raw BackendArticleDTO -> CanonicalArticle
 */
export function normalizeCanonicalArticle(dto: BackendArticleDTO | null | undefined): CanonicalArticle {
  if (!dto) {
    return {
      id: "unknown",
      title: "Untitled Story",
      image: null,
      imageSource: "fallback",
    };
  }

  // Extract clean ID
  const id = dto.id !== undefined && dto.id !== null ? dto.id : 0;

  // Extract clean slug
  const rawSlug = dto.slug;
  const cleanSlug = typeof rawSlug === "string" && rawSlug.trim() !== "" && !rawSlug.startsWith("http")
    ? rawSlug.trim()
    : undefined;

  // Extract clean category
  let category: string | null = null;
  if (typeof dto.category === "string" && dto.category.trim() !== "") {
    category = dto.category.trim();
  } else if (typeof dto.category === "object" && dto.category?.name) {
    category = dto.category.name;
  }

  // Extract clean source name
  let sourceName: string | null = null;
  if (dto.source_name && typeof dto.source_name === "string" && dto.source_name.trim() !== "") {
    sourceName = dto.source_name.trim();
  } else if (typeof dto.source === "string" && dto.source.trim() !== "") {
    sourceName = dto.source.trim();
  } else if (typeof dto.source === "object" && dto.source?.name) {
    sourceName = dto.source.name;
  } else if (dto.source_domain) {
    sourceName = dto.source_domain;
  }

  // Resolve media using MediaService
  const media = MediaService.resolve(dto);

  return {
    id,
    slug: cleanSlug,
    title: dto.title || "Untitled Story",
    summary: dto.summary || dto.description || null,
    category,
    image: media.url,
    imageSource: media.source,
    publishedAt: dto.published_at || null,
    source: sourceName,
    url: dto.url || null,
    readTime: dto.read_time ?? dto.reading_time ?? 3,
    documentType: dto.document_type || null,
    isMultiTopic: dto.is_multi_topic ?? null,
    primaryTopics: dto.primary_topics || null,
    dominantTopicPercentage: dto.dominant_topic_percentage ?? null,
    reason: dto.reason || null,
  };
}
