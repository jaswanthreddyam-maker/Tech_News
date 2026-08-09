/**
 * normalizeUploadPath — Encapsulates backend storage path transformations
 * e.g., transforms container path '/app/uploads/' to public route '/api/v1/uploads/'
 */
export function normalizeUploadPath(path: string | null | undefined): string | null {
  if (!path) return null;
  const trimmed = path.trim();
  if (!trimmed) return null;

  if (trimmed.startsWith("/app/uploads/")) {
    return trimmed.replace("/app/uploads/", "/api/v1/uploads/");
  }

  return trimmed;
}
