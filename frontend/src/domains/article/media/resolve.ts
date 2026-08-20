import { BackendArticleDTO, ResolvedMedia } from "../types";
import { normalizeUploadPath } from "./normalizePath";
import { isFailed } from "./failedImages";
import { getCategoryFallbackImage } from "./categoryFallbacks";

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

  // Priority 5: cover_image
  if (dto.cover_image) {
    const norm = normalizeUploadPath(dto.cover_image);
    if (norm && !isFailed(norm)) {
      return { url: norm, source: "cover_image" };
    }
  }

  // Priority 6: Themed Category HD Editorial Fallback
  const fallbackUrl = getCategoryFallbackImage(dto.category, dto.id || dto.title);
  if (fallbackUrl) {
    return { url: fallbackUrl, source: "category_fallback" };
  }

  // Final Fallback
  return { url: null, source: "fallback" };
}

/**
 * hasGenuineThumbnail — Checks if an article possesses a genuine, verified publisher editorial image.
 * Returns false if the article would otherwise rely on synthetic or category fallback images.
 */
export function hasGenuineThumbnail(dto: any): boolean {
  if (!dto) return false;
  const isVal = (u?: string | null) => 
    Boolean(u && typeof u === "string" && (u.startsWith("http://") || u.startsWith("https://")) && !u.includes("example.com") && !isFailed(u));

  if (isVal(dto.thumbnail_url)) return true;
  if (isVal(dto.image_url)) return true;
  if (dto.hero_image && !isFailed(normalizeUploadPath(dto.hero_image) || "")) return true;
  if (dto.thumbnail_local && !isFailed(normalizeUploadPath(dto.thumbnail_local) || "")) return true;
  if (dto.cover_image && !isFailed(normalizeUploadPath(dto.cover_image) || "")) return true;
  if (isVal(dto.thumbnail)) return true;
  if (isVal(dto.image)) return true;

  return false;
}
