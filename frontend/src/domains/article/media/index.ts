import { resolve } from "./resolve";
import { normalizeUploadPath } from "./normalizePath";
import { markFailed, isFailed } from "./failedImages";

export { resolve } from "./resolve";
export { normalizeUploadPath } from "./normalizePath";
export { markFailed, isFailed } from "./failedImages";

/**
 * MediaService — Modular Media Infrastructure Namespace
 */
export const MediaService = {
  resolve,
  normalizeUploadPath,
  markFailed,
  isFailed,
} as const;
