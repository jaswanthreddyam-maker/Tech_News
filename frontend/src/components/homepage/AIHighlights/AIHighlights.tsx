"use client";

import { useAIHighlights } from "@/components/hooks/articles/useArticles";
import { Skeleton } from "@/design-system/components/Skeleton";
import { useLoadingState } from "@/design-system/hooks/useLoadingState";
import { Sparkles, Activity, Tag, Info } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { useQuery } from "@tanstack/react-query";
import { getArticles, getTrendingArticles } from "@/lib/api/articles";

function getConfidenceBar(confidence: number) {
  const filled = Math.round(confidence / 10);
  return '█'.repeat(filled) + '░'.repeat(10 - filled);
}

export function AIHighlights() {
  const aiQuery = useAIHighlights();

  // Fallbacks in order of priority: AI Articles -> Editor's Picks -> Trending -> Latest
  const featuredQuery = useQuery({
    queryKey: ["articles", "featured-fallback"],
    queryFn: () => getArticles({ limit: 4 }),
    enabled: !aiQuery.isLoading && (!aiQuery.data?.data || aiQuery.data.data.length === 0),
  });

  const trendingQuery = useQuery({
    queryKey: ["articles", "trending-fallback"],
    queryFn: () => getTrendingArticles(),
    enabled: !aiQuery.isLoading && (!aiQuery.data?.data || aiQuery.data.data.length === 0) && (!featuredQuery.data?.data || featuredQuery.data.data.length === 0),
  });

  const latestQuery = useQuery({
    queryKey: ["articles", "latest-fallback"],
    queryFn: () => getArticles({ limit: 4 }),
    enabled: !aiQuery.isLoading && (!aiQuery.data?.data || aiQuery.data.data.length === 0) && (!featuredQuery.data?.data || featuredQuery.data.data.length === 0) && (!trendingQuery.data?.data || trendingQuery.data.data.length === 0),
  });

  const isLoading = aiQuery.isLoading || 
                    (aiQuery.data?.data?.length === 0 && featuredQuery.isLoading) ||
                    (aiQuery.data?.data?.length === 0 && featuredQuery.data?.data?.length === 0 && trendingQuery.isLoading) ||
                    (aiQuery.data?.data?.length === 0 && featuredQuery.data?.data?.length === 0 && trendingQuery.data?.data?.length === 0 && latestQuery.isLoading);

  const loadingLevel = useLoadingState(isLoading);

  if (isLoading) {
    return (
      <div className="bg-card border border-border/80 p-6 h-full flex flex-col relative overflow-hidden rounded-xl">
        <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 blur-3xl rounded-full" />
        <div className="flex items-center justify-between mb-6 border-b border-border/55 pb-4">
          <div className="flex items-center gap-2">
            <Skeleton level={loadingLevel} className="w-5 h-5 rounded-full" />
            <Skeleton level={loadingLevel} className="h-6 w-40" />
          </div>
          <Skeleton level={loadingLevel} className="h-5 w-20 rounded-full" />
        </div>
        <div className="flex-1 space-y-8">
          {[1, 2].map((i) => (
            <div key={i} className="relative z-10">
              <Skeleton level={loadingLevel} className="h-5 w-full mb-2" />
              <Skeleton level={loadingLevel} className="h-5 w-3/4 mb-4" />
              <div className="flex flex-wrap gap-2 mb-4">
                <Skeleton level={loadingLevel} className="h-4 w-16 rounded-full" />
                <Skeleton level={loadingLevel} className="h-4 w-20 rounded-full" />
                <Skeleton level={loadingLevel} className="h-4 w-16 rounded-full" />
              </div>
              <div className="bg-muted/30 rounded p-3 border border-border/40">
                <div className="flex items-center gap-1.5 mb-3">
                  <Skeleton level={loadingLevel} className="h-4 w-4 rounded-full" />
                  <Skeleton level={loadingLevel} className="h-3 w-24" />
                </div>
                <div className="space-y-2">
                  <Skeleton level={loadingLevel} className="h-3 w-full" />
                  <Skeleton level={loadingLevel} className="h-3 w-5/6" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Resolve the active data list
  let articles = aiQuery.data?.data || [];
  let sourceBadge = "AI Analysis";

  if (articles.length === 0 && featuredQuery.data?.data && featuredQuery.data.data.length > 0) {
    articles = featuredQuery.data.data;
    sourceBadge = "Editor's Picks";
  }

  if (articles.length === 0 && trendingQuery.data?.data && trendingQuery.data.data.length > 0) {
    articles = trendingQuery.data.data;
    sourceBadge = "Trending";
  }

  if (articles.length === 0 && latestQuery.data?.data && latestQuery.data.data.length > 0) {
    articles = latestQuery.data.data;
    sourceBadge = "Latest News";
  }

  if (articles.length === 0) {
    return (
      <div className="bg-card border border-border p-6 h-full flex items-center justify-center text-muted-foreground">
        No insights available at this time.
      </div>
    );
  }

  // Show top 2 insights
  const insights = articles.slice(0, 2);

  return (
    <div className="bg-card border border-border/80 p-6 h-full flex flex-col relative overflow-hidden rounded-xl">
      {/* Background decoration */}
      <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 blur-3xl rounded-full" />
      
      <div className="flex items-center justify-between mb-6 border-b border-border/55 pb-4">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-primary" />
          <h3 className="font-sans font-bold text-lg text-foreground tracking-tight">
            Today&apos;s AI Insights
          </h3>
        </div>
        <Badge variant="secondary" className="text-[10px] font-mono tracking-wider">
          {sourceBadge}
        </Badge>
      </div>

      <div className="flex-1 space-y-8">
        {insights.map((article) => (
          <div key={article.id} className="relative z-10">
            <Link href={`/articles/${article.slug}`} className="group">
              <h4 className="font-serif font-bold text-base text-card-foreground leading-snug group-hover:text-primary transition-colors mb-3">
                {article.title}
              </h4>
            </Link>

            <div className="flex flex-wrap gap-2 mb-4">
              {article.ai_confidence && (
                <Badge variant="outline" className="text-[9px] font-mono border-primary/30 text-primary bg-primary/5 tracking-wider">
                  {getConfidenceBar(article.ai_confidence)} {article.ai_confidence}%
                </Badge>
              )}
              {article.sentiment && (
                <Badge variant="outline" className="text-[9px] font-mono border-border text-muted-foreground">
                  <Activity className="w-3 h-3 mr-1 inline" />
                  {article.sentiment}
                </Badge>
              )}
              {article.category && (
                <Badge variant="outline" className="text-[9px] font-mono border-border text-muted-foreground">
                  <Tag className="w-3 h-3 mr-1 inline" />
                  {article.category}
                </Badge>
              )}
            </div>

            {article.why_this_matters && article.why_this_matters.length > 0 ? (
              <div className="bg-muted/30 rounded p-3 border border-border/40">
                <div className="flex items-center gap-1.5 mb-2">
                  <Info className="w-3.5 h-3.5 text-primary" />
                  <span className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground font-semibold">
                    Why this matters
                  </span>
                </div>
                <ul className="space-y-1.5">
                  {article.why_this_matters.slice(0, 2).map((point, idx) => (
                    <li key={idx} className="flex items-start gap-1.5 text-xs text-muted-foreground">
                      <span className="text-primary mt-0.5">•</span>
                      <span className="line-clamp-2">{point}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground line-clamp-2">{article.summary}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
