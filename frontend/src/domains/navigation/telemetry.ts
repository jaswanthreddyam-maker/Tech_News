import { NavigationTelemetryPayload } from "./types";

/**
 * reportNavigationError — Reports navigation data anomalies for telemetry/Sentry monitoring
 */
export function reportNavigationError(payload: NavigationTelemetryPayload): void {
  if (process.env.NODE_ENV !== "production") {
    // eslint-disable-next-line no-console
    console.warn("[Navigation Telemetry Warning]", {
      articleId: payload.articleId,
      slug: payload.slug,
      reason: payload.reason,
      component: payload.component || "UnknownComponent",
      timestamp: new Date().toISOString(),
    });
  }

  // Hook for production error tracking (Sentry / Datadog / OpenTelemetry)
  if (typeof window !== "undefined" && (window as any).__TNT_TELEMETRY__) {
    try {
      (window as any).__TNT_TELEMETRY__.captureException(new Error(`Navigation Error: ${payload.reason}`), {
        extra: payload,
      });
    } catch {}
  }
}
