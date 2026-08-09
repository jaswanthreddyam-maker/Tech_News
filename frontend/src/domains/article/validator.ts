import { CanonicalArticle } from "./types";

/**
 * validateCanonicalArticles — Development-only runtime assertion helper (tree-shaken in production)
 */
export function validateCanonicalArticles(articles: CanonicalArticle[]): void {
  if (process.env.NODE_ENV !== "development") {
    return;
  }

  const seenSlugs = new Set<string>();
  const seenImages = new Set<string>();

  articles.forEach((article, idx) => {
    // 1. Slug validation
    if (article.slug) {
      if (seenSlugs.has(article.slug)) {
        // eslint-disable-next-line no-console
        console.warn(`[DEV ASSERTION WARN] Duplicate slug detected at index ${idx}: "${article.slug}"`);
      } else {
        seenSlugs.add(article.slug);
      }
    } else {
      // eslint-disable-next-line no-console
      console.warn(`[DEV ASSERTION WARN] Article ID ${article.id} missing canonical slug at index ${idx}`);
    }

    // 2. Image validation
    if (article.image) {
      if (seenImages.has(article.image)) {
        // eslint-disable-next-line no-console
        console.warn(`[DEV ASSERTION WARN] Duplicate image URL detected at index ${idx}: "${article.image}" (Title: "${article.title}")`);
      } else {
        seenImages.add(article.image);
      }

      if (article.image.startsWith("javascript:") || article.image.startsWith("data:")) {
        // eslint-disable-next-line no-console
        console.warn(`[DEV ASSERTION WARN] Invalid image protocol scheme at index ${idx}: "${article.image}"`);
      }
    } else {
      // eslint-disable-next-line no-console
      console.info(`[DEV ASSERTION INFO] Article ID ${article.id} ("${article.title.substring(0, 25) || ""}") missing primary media asset — will render CategoryPlaceholder.`);
    }
  });
}
