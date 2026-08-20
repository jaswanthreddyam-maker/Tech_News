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

  // Client-side in browser: use relative proxy path /api/v1
  let envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!envUrl || envUrl.includes("<") || envUrl.includes("your-railway")) {
    return "/api/v1";
  }
  envUrl = envUrl.trim().replace(/\/+$/, "");
  if (!envUrl.endsWith("/api/v1") && !envUrl.startsWith("/")) {
    envUrl = `${envUrl}/api/v1`;
  }
  return envUrl;
}
