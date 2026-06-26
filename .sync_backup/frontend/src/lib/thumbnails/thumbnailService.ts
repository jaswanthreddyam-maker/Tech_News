interface ArticleThumbnailData {
  thumbnail_local?: string | null;
  thumbnail_url?: string | null;
  image_url?: string | null;
  category?: string;
  thumbnail_source?: string;
}

export interface ThumbnailResolution {
  src: string | null;
  isFallback: boolean;
  blurDataURL?: string;
  source: string;
}

// Client-side in-memory cache of failed image URLs
const failedUrls = new Set<string>();

// Generic dark gray 10x10 base64 placeholder for Next.js blurDataURL
const GENERIC_BLUR = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=";

export const thumbnailService = {
  resolveThumbnail(article: ArticleThumbnailData): ThumbnailResolution {
    const localUrl = article?.thumbnail_local;
    const url = article?.thumbnail_url || article?.image_url;

    // 1. Try external/api thumbnail_url
    if (url && !failedUrls.has(url)) {
      return {
        src: url,
        isFallback: false,
        blurDataURL: GENERIC_BLUR,
        source: article?.thumbnail_source || "external"
      };
    }

    // 2. Fall back to thumbnail_local
    if (localUrl && !failedUrls.has(localUrl)) {
      return {
        src: localUrl,
        isFallback: false,
        blurDataURL: GENERIC_BLUR,
        source: article?.thumbnail_source || "local"
      };
    }

    // 3. Fallback
    return {
      src: null,
      isFallback: true,
      source: "fallback"
    };
  },

  markAsFailed(url: string) {
    if (!url) return;
    failedUrls.add(url);
  }
};
