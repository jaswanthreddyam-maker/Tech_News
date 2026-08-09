import { CanonicalArticle } from "../article/types";
import { ResolvedArticleRoute } from "./types";

/**
 * resolveArticleRoute — 100% Pure Route Resolver (Zero side effects)
 * 
 * Classifies any given article object into a deterministic navigation target:
 * - "internal": Clean internal Next.js article route (/articles/[slug])
 * - "external": Original publisher URL (target="_blank", rel="noopener noreferrer")
 * - "invalid": Missing/corrupted slug & URL, or blocked dangerous protocol
 */
export function resolveArticleRoute(article: CanonicalArticle | null | undefined): ResolvedArticleRoute {
  if (!article) {
    return {
      kind: "invalid",
      href: "#",
      reason: "Article object is null or undefined",
    };
  }

  const rawSlug = article.slug;
  const rawUrl = article.url;
  const rawId = article.id;

  const effectiveSlug =
    typeof rawSlug === "string" && rawSlug.trim().length > 0
      ? rawSlug.trim()
      : rawId !== null &&
        rawId !== undefined &&
        String(rawId).trim().length > 0 &&
        String(rawId).trim() !== "null" &&
        String(rawId).trim() !== "undefined"
      ? String(rawId).trim()
      : "";

  // 1. Check for valid internal slug or article ID fallback
  if (effectiveSlug.length > 0) {
    if (
      !effectiveSlug.startsWith("http://") &&
      !effectiveSlug.startsWith("https://") &&
      !effectiveSlug.startsWith("javascript:") &&
      !effectiveSlug.startsWith("data:") &&
      !effectiveSlug.startsWith("ftp:")
    ) {
      return {
        kind: "internal",
        href: `/articles/${encodeURIComponent(effectiveSlug)}`,
      };
    }
  }

  // 2. Check for valid external publisher URL
  if (typeof rawUrl === "string") {
    const trimmedUrl = rawUrl.trim();
    if (trimmedUrl.startsWith("http://") || trimmedUrl.startsWith("https://")) {
      return {
        kind: "external",
        href: trimmedUrl,
        target: "_blank",
        rel: "noopener noreferrer",
      };
    }

    // Security check: explicitly block dangerous protocols
    if (
      trimmedUrl.startsWith("javascript:") ||
      trimmedUrl.startsWith("data:") ||
      trimmedUrl.startsWith("ftp:")
    ) {
      return {
        kind: "invalid",
        href: "#",
        reason: `Blocked unsafe protocol in URL: ${trimmedUrl.split(":")[0]}`,
      };
    }
  }

  // 3. Invalid route classification
  return {
    kind: "invalid",
    href: "#",
    reason: `Article ID ${article.id || "unknown"} is missing a canonical slug and valid publisher URL`,
  };
}
