import { MetadataRoute } from 'next';

const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000';
const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

// The max size per sitemap supported by search engines is 50,000 URLs.
// We chunk articles by 10,000 to be safe.
export async function generateSitemaps() {
  // Normally we would query the backend to find total articles
  // For the initial release, we return a static array of ids
  return [{ id: 0 }];
}

export default async function sitemap({
  id,
}: {
  id: number;
}): Promise<MetadataRoute.Sitemap> {
  // Fetch articles from our API
  const start = id * 10000;
  
  let articles = [];
  try {
    const res = await fetch(`${apiBaseUrl}/api/v1/news?limit=100`, {
      next: { revalidate: 3600 }, // Cache for 1 hour
    });
    
    if (res.ok) {
      const json = await res.json();
      articles = json.data || [];
    }
  } catch (err) {
    console.error("Failed to fetch articles for sitemap", err);
  }

  const sitemapEntries: MetadataRoute.Sitemap = articles.map((article: any) => ({
    url: `${baseUrl}/articles/${article.id}`,
    lastModified: article.published_at || new Date().toISOString(),
    changeFrequency: 'daily' as const,
    priority: 0.8,
  }));

  // Add static routes if this is the first chunk
  if (id === 0) {
    sitemapEntries.unshift({
      url: `${baseUrl}`,
      lastModified: new Date().toISOString(),
      changeFrequency: 'hourly' as const,
      priority: 1.0,
    });
    sitemapEntries.push({
      url: `${baseUrl}/editorial`,
      lastModified: new Date().toISOString(),
      changeFrequency: 'daily' as const,
      priority: 0.8,
    });
  }

  return sitemapEntries;
}
