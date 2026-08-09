// In-memory failure cache map storing URL -> failure timestamp
const failedImages = new Map<string, number>();

// 10-minute TTL pruning window (600,000 ms)
const FAILURE_TTL_MS = 10 * 60 * 1000;

function pruneExpiredFailures(now: number): void {
  failedImages.forEach((timestamp, url) => {
    if (now - timestamp > FAILURE_TTL_MS) {
      failedImages.delete(url);
    }
  });
}

/**
 * markFailed — Caches a failed image URL to prevent infinite retries
 */
export function markFailed(url: string | null | undefined): void {
  if (!url) return;
  const now = Date.now();
  pruneExpiredFailures(now);
  failedImages.set(url, now);
}

/**
 * isFailed — Checks if an image URL has previously failed and is currently cached
 */
export function isFailed(url: string | null | undefined): boolean {
  if (!url) return false;
  const now = Date.now();
  pruneExpiredFailures(now);

  const timestamp = failedImages.get(url);
  if (!timestamp) return false;

  if (now - timestamp > FAILURE_TTL_MS) {
    failedImages.delete(url);
    return false;
  }

  return true;
}
