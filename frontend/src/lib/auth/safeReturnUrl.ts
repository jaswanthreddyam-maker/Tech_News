/**
 * Validates and sanitizes a returnUrl / redirect parameter to ensure it is strictly
 * an internal relative application path, preventing Open Redirect vulnerabilities.
 */
export function sanitizeReturnUrl(value: string | null | undefined): string {
  if (!value || typeof value !== "string") {
    return "/";
  }

  const trimmed = value.trim();

  // Must start with single forward slash and not protocol-relative (//) or backslash (\)
  if (
    !trimmed.startsWith("/") ||
    trimmed.startsWith("//") ||
    trimmed.startsWith("/\\") ||
    trimmed.startsWith("\\") ||
    /^[/\\\\]{2,}/.test(trimmed)
  ) {
    return "/";
  }

  // Reject control characters or newlines
  if (/[\r\n\t]/.test(trimmed)) {
    return "/";
  }

  try {
    // Parse against a dummy base origin to verify structure
    const parsed = new URL(trimmed, "http://localhost");

    // The origin must match the dummy origin (ensures no domain escaping)
    if (parsed.origin !== "http://localhost") {
      return "/";
    }

    // Reconstruct safe relative path (pathname + search + hash)
    const safePath = parsed.pathname + parsed.search + parsed.hash;
    return safePath.startsWith("/") && !safePath.startsWith("//") ? safePath : "/";
  } catch {
    return "/";
  }
}
