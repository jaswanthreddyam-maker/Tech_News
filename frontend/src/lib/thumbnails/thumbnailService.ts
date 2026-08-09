interface ArticleThumbnailData {
  thumbnail_local?: string | null;
  thumbnail_url?: string | null;
  image_url?: string | null;
  thumbnail_status?: string | null;
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
  getPublicImageUrl(article: ArticleThumbnailData | null | undefined): string | null {
    if (!article) return null;

    // 1. Primary: Prefer local processed WebP thumbnail asset if present and downloaded/valid
    if (article.thumbnail_local && (article.thumbnail_status === "downloaded" || !article.thumbnail_status)) {
      let localUrl = article.thumbnail_local;
      if (localUrl.startsWith('/app/uploads/')) {
        localUrl = localUrl.replace('/app/uploads/', '/api/v1/uploads/');
      }
      if (!failedUrls.has(localUrl)) {
        return localUrl;
      }
    }

    // 2. Secondary Fallback: Remote publisher HTTP URL
    if (article.thumbnail_url && !failedUrls.has(article.thumbnail_url)) {
      return article.thumbnail_url;
    }

    // 3. Legacy Fallback: image_url
    if (article.image_url && !failedUrls.has(article.image_url)) {
      return article.image_url;
    }

    return null;
  },

  resolveThumbnail(article: ArticleThumbnailData | null | undefined): ThumbnailResolution {
    const publicUrl = this.getPublicImageUrl(article);

    // 1. Try public routable URL
    if (publicUrl && !failedUrls.has(publicUrl)) {
      return {
        src: publicUrl,
        isFallback: false,
        blurDataURL: GENERIC_BLUR,
        source: article?.thumbnail_source || "external"
      };
    }

    // 2. Fallback
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
