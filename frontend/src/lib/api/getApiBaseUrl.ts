export function getApiBaseUrl(): string {
  let envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!envUrl || envUrl.includes("<") || envUrl.includes("your-railway")) {
    return "https://tech-news-api-production-1b42.up.railway.app/api/v1";
  }
  envUrl = envUrl.trim().replace(/\/+$/, "");
  if (!envUrl.endsWith("/api/v1")) {
    envUrl = `${envUrl}/api/v1`;
  }
  return envUrl;
}
