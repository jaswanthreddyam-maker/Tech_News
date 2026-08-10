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

  // Priority 1: thumbnail_url (Public HTTPS CDN URL)
  if (dto.thumbnail_url && (dto.thumbnail_url.startsWith("http://") || dto.thumbnail_url.startsWith("https://"))) {
    if (!isFailed(dto.thumbnail_url)) {
      return { url: dto.thumbnail_url, source: "thumbnail_url" };
    }
  }

  // Priority 2: image_url (Public HTTPS CDN URL)
  if (dto.image_url && (dto.image_url.startsWith("http://") || dto.image_url.startsWith("https://"))) {
    if (!isFailed(dto.image_url)) {
      return { url: dto.image_url, source: "image_url" };
    }
  }

  // Priority 3: hero_image
  if (dto.hero_image) {
    const norm = normalizeUploadPath(dto.hero_image);
    if (norm && !isFailed(norm)) {
      return { url: norm, source: "hero_image" };
    }
  }

  // Priority 4: thumbnail_local (Container local file path)
  if (dto.thumbnail_local) {
    const norm = normalizeUploadPath(dto.thumbnail_local);
    if (norm && !isFailed(norm)) {
      return { url: norm, source: "thumbnail_local" };
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
