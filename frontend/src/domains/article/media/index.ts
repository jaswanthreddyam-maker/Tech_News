import { resolve, hasGenuineThumbnail } from "./resolve";
import { normalizeUploadPath } from "./normalizePath";
import { markFailed, isFailed } from "./failedImages";
import { getCategoryFallbackImage } from "./categoryFallbacks";

export { resolve, hasGenuineThumbnail } from "./resolve";
export { normalizeUploadPath } from "./normalizePath";
export { markFailed, isFailed } from "./failedImages";
export { getCategoryFallbackImage } from "./categoryFallbacks";

/**
 * MediaService — Modular Media Infrastructure Namespace
 */
export const MediaService = {
  resolve,
  hasGenuineThumbnail,
  normalizeUploadPath,
  markFailed,
  isFailed,
  getCategoryFallbackImage,
} as const;
