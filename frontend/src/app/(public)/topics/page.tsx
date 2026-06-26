import { Container } from "@/components/layout/Container";
import { getArticles, getTrends } from "@/lib/api/articles";
import { apiFetch } from "@/lib/api/client";
import Link from "next/link";
import { TrendingUp, AlertCircle, Clock, ExternalLink } from "lucide-react";
import { CategoryGrid } from "./CategoryGrid";
import { Article } from "@/lib/api/types";

interface Category {
  id: number;
  name: string;
  slug: string;
}

export const metadata = {
  title: "Explore Topics | Tech News Today",
  description: "Browse all technology news categories, trending concepts, and AI analysis.",
};

export const revalidate = 60; // Revalidate page cache every minute

export default async function TopicsPage() {
  let categories: Category[] = [];
  try {
    categories = await apiFetch<Category[]>("/categories");
  } catch (err) {
    // eslint-disable-next-line no-console

  }

  // Fetch latest articles and compute real metadata for each category
  const categoriesWithArticles = await Promise.all(
    categories.map(async (cat) => {
      try {
        const response = await getArticles({ category: cat.slug, limit: 10 });
        const list = response.data || [];
        const hasMore = response.pagination?.has_more || false;
        const totalCount = hasMore ? 10 : list.length;
        
        const lastUpdatedDate = list[0]?.published_at;
        let lastUpdatedStr: string | null = null;
        if (lastUpdatedDate) {
          const elapsedMs = Date.now() - new Date(lastUpdatedDate).getTime();
          const elapsedHours = Math.floor(elapsedMs / (1000 * 60 * 60));
          if (elapsedHours < 24) {
            lastUpdatedStr = elapsedHours === 0 ? "just now" : `${elapsedHours}h ago`;
          } else {
            const elapsedDays = Math.floor(elapsedHours / 24);
            lastUpdatedStr = `${elapsedDays}d ago`;
          }
        }

        return {
          ...cat,
          articles: list.slice(0, 3), // Show top 3 in the UI
          totalCount,
          lastUpdated: lastUpdatedStr,
        };
      } catch (err) {
        // eslint-disable-next-line no-console

        return {
          ...cat,
          articles: [],
          totalCount: 0,
          lastUpdated: null,
        };
      }
    })
  );

  return (
    <Container className="py-10 space-y-12 min-h-screen transition-colors duration-300">
      <CategoryGrid categories={categoriesWithArticles as any} />

      {/* Trending Topics Section (Progressive Enhancement) */}
      <TrendingTopicsSection />

      {/* Latest Global Articles Section */}
      <LatestArticlesSection />
    </Container>
  );
}

async function TrendingTopicsSection() {
  let trends: string[] = [];
  let error = false;

  try {
    trends = await getTrends();
  } catch {
    // Graceful error logging
    error = true;
  }

  // Graceful degradation logic
  if (error || !trends || trends.length === 0) {
    return (
      <div className="border border-neutral-900 bg-neutral-950/20 p-6 rounded-xl space-y-4">
        <div className="flex items-center gap-3">
          <TrendingUp className="w-5 h-5 text-muted-foreground/60" />
          <h3 className="text-base font-bold text-muted-foreground/80">Trending Topics</h3>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground/50 font-mono">
          <AlertCircle className="w-4 h-4 text-muted-foreground/45 shrink-0" />
          <span>Trending topics are currently unavailable. Check back later as more activity is collected.</span>
        </div>
      </div>
    );
  }

  return (
    <div className="border border-neutral-900 bg-neutral-950/30 p-6 rounded-xl space-y-4 shadow-md">
      <div className="flex items-center gap-3">
        <TrendingUp className="w-5 h-5 text-primary" />
        <h3 className="text-base font-bold text-white">Trending Topics</h3>
      </div>
      <div className="flex flex-wrap gap-2">
        {trends.map((tag) => (
          <Link
            key={tag}
            href={`/search?q=${encodeURIComponent(tag)}`}
            className="text-xs font-mono bg-neutral-900 hover:bg-neutral-800 border border-neutral-850 hover:border-neutral-700 px-3 py-1.5 rounded-full text-foreground/80 hover:text-primary transition-all duration-200"
          >
            #{tag}
          </Link>
        ))}
      </div>
    </div>
  );
}

async function LatestArticlesSection() {
  let articles: Article[] = [];
  try {
    const res = await getArticles({ limit: 4 });
    articles = res.data || [];
  } catch (err) {
    // eslint-disable-next-line no-console

    return (
      <div className="p-6 border border-neutral-900 bg-neutral-950/20 text-muted-foreground/60 rounded-xl text-center font-mono text-xs">
        Latest articles feed is currently offline.
      </div>
    );
  }

  if (articles.length === 0) {
    return null;
  }

  return (
    <div className="space-y-6">
      <div className="border-b border-neutral-900 pb-3 flex items-center justify-between">
        <h3 className="text-lg font-bold flex items-center gap-2 text-white">
          <Clock className="w-5 h-5 text-primary" />
          Latest in Tech News
        </h3>
        <span className="text-xs font-mono text-muted-foreground/60">Real-time Feed</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {articles.map((art) => (
          <div
            key={art.id}
            className="group border border-neutral-900 bg-[#0c0c0c]/40 hover:bg-[#0c0c0c]/80 p-5 rounded-xl hover:border-neutral-800 transition-all flex flex-col justify-between shadow-sm"
          >
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono uppercase tracking-wider bg-neutral-900 border border-neutral-800 px-2 py-0.5 rounded text-primary">
                  {art.category}
                </span>
                <span className="text-[10px] font-mono text-muted-foreground/40" suppressHydrationWarning>
                  {art.published_at
                    ? new Date(art.published_at).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                        timeZone: "UTC"
                      })
                    : ""}
                </span>
              </div>
              <Link href={`/articles/${art.slug}`} className="block">
                <h4 className="font-bold text-base leading-snug text-[#f2f2f2] group-hover:text-primary transition-colors line-clamp-2">
                  {art.title}
                </h4>
              </Link>
              <p className="text-sm text-muted-foreground/75 line-clamp-2 leading-relaxed">
                {art.summary}
              </p>
            </div>
            
            <div className="pt-4 flex items-center justify-between text-xs text-muted-foreground/60 border-t border-neutral-950 mt-4">
              <span className="font-mono text-[10px] text-muted-foreground/50">Compiled by: {art.source || "System"}</span>
              <Link
                href={`/articles/${art.slug}`}
                className="font-semibold text-primary group-hover:underline flex items-center gap-1"
              >
                Read Story <ExternalLink className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
