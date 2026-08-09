import { ArticleClickAnalyticsPayload } from "./types";

/**
 * trackArticleClick — Emits analytics click event for article navigation
 */
export function trackArticleClick(payload: ArticleClickAnalyticsPayload): void {
  if (process.env.NODE_ENV !== "production") {
    // eslint-disable-next-line no-console
    console.log("[Navigation Analytics Click]", payload);
  }

  if (typeof window !== "undefined") {
    // Custom DOM event for offline tracking queue
    window.dispatchEvent(
      new CustomEvent("tnt:article_click", {
        detail: {
          ...payload,
          timestamp: new Date().toISOString(),
        },
      })
    );
  }
}
