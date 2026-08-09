export function getApiBaseUrl(): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!envUrl || envUrl.includes("<") || envUrl.includes("your-railway")) {
    return "https://tech-news-api-production-1b42.up.railway.app/api/v1";
  }
  return envUrl;
}
