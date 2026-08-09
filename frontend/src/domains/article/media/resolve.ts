import { BackendArticleDTO, ResolvedMedia } from "../types";
import { normalizeUploadPath } from "./normalizePath";
import { isFailed } from "./failedImages";

/**
 * resolve — Pure media resolution logic evaluating DTO fields in priority order
 */
export function resolve(dto: BackendArticleDTO | null | undefined): ResolvedMedia {
  if (!dto) {
    return { url: null, source: "fallback" };
  }

  // Priority 1: hero_image
  if (dto.hero_image) {
    const norm = normalizeUploadPath(dto.hero_image);
    if (norm && !isFailed(norm)) {
      return { url: norm, source: "hero_image" };
    }
  }

  // Priority 2: thumbnail_local
  if (dto.thumbnail_local) {
    const norm = normalizeUploadPath(dto.thumbnail_local);
    if (norm && !isFailed(norm)) {
      return { url: norm, source: "thumbnail_local" };
    }
  }

  // Priority 3: thumbnail_url
  if (dto.thumbnail_url) {
    const norm = normalizeUploadPath(dto.thumbnail_url);
    if (norm && !isFailed(norm)) {
      return { url: norm, source: "thumbnail_url" };
    }
  }

  // Priority 4: image_url
  if (dto.image_url) {
    const norm = normalizeUploadPath(dto.image_url);
    if (norm && !isFailed(norm)) {
      return { url: norm, source: "image_url" };
    }
  }

  // Priority 5: cover_image
  if (dto.cover_image) {
    const norm = normalizeUploadPath(dto.cover_image);
    if (norm && !isFailed(norm)) {
      return { url: norm, source: "cover_image" };
    }
  }

  // Fallback
  return { url: null, source: "fallback" };
}
