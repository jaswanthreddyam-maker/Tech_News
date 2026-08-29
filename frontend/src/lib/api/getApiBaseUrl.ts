export function getApiBaseUrl(): string {
  if (typeof window === "undefined") {
    // Server-side (Node.js SSR) requires absolute URL
    const isProd = process.env.NODE_ENV === "production" || process.env.VERCEL === "1";
    const defaultBackend = isProd 
      ? "https://technews-production-d18d.up.railway.app" 
      : "http://localhost:8000";

    const serverUrl =
      process.env.INTERNAL_API_URL ||
      process.env.API_PROXY_TARGET ||
      process.env.NEXT_PUBLIC_API_BASE_URL ||
      defaultBackend;
    const trimmed = serverUrl.trim().replace(/\/+$/, "");
    return trimmed.endsWith("/api/v1") ? trimmed : `${trimmed}/api/v1`;
  }

  // Client-side in browser: ALWAYS use relative proxy path /api/v1
  // This ensures requests go through Next.js rewrites (configured in next.config.js)
  // which proxy to the backend, avoiding CORS issues entirely.
  // Using an absolute backend URL here would bypass the proxy and trigger CORS blocks
  // since the Railway backend doesn't allow arbitrary Vercel preview origins.
  return "/api/v1";
}
