"use client";

import { usePersonalizedFeed } from "@/components/hooks/articles/useArticles";
import { Skeleton } from "@/design-system/components/Skeleton";
import { useLoadingState } from "@/design-system/hooks/useLoadingState";
import Link from "next/link";
import { Clock, TrendingUp, Sparkles, Eye, Newspaper } from "lucide-react";
import { EmptyState, EmptyIllustration } from "@/components/common/EmptyState";
import { useEffect, useState } from "react";
import { ArticleThumbnail } from "@/components/common/ArticleThumbnail";
import { useOfflineQueue } from "@/components/reading/tracker/useOfflineQueue";
import { Reveal, StaggerContainer, StaggerItem } from "@/components/animations";

export function TrendingStories() {
  const [anonId, setAnonId] = useState<string | null>(null);
  const { enqueue } = useOfflineQueue();
  
  useEffect(() => {
    if (typeof window !== 'undefined') {
      setAnonId(localStorage.getItem('tnt_anon_id'));
    }
  }, []);

  const { data, isLoading, error } = usePersonalizedFeed(anonId);
  const loadingLevel = useLoadingState(isLoading);

  if (isLoading) {
    return (
      <section className="py-8 border-t border-border mt-8">
        <div className="flex items-center gap-3 mb-8">
          <Skeleton level={loadingLevel} className="w-9 h-9 rounded-lg" />
          <Skeleton level={loadingLevel} className="h-8 w-48" />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Featured Card Skeleton */}
          <div className="lg:col-span-5 border border-border bg-card">
            <Skeleton level={loadingLevel} className="aspect-video w-full rounded-none" />
            <div className="p-6">
              <Skeleton level={loadingLevel} className="h-3 w-20 mb-4" />
              <Skeleton level={loadingLevel} className="h-8 w-full mb-2" />
              <Skeleton level={loadingLevel} className="h-8 w-3/4 mb-4" />
              <Skeleton level={loadingLevel} className="h-4 w-full mb-2" />
              <Skeleton level={loadingLevel} className="h-4 w-full mb-2" />
              <Skeleton level={loadingLevel} className="h-4 w-2/3 mb-4" />
              <Skeleton level={loadingLevel} className="h-8 w-32 mt-6" />
            </div>
          </div>
          {/* Compact Cards Skeleton */}
          <div className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="flex flex-col p-4 border border-border bg-card h-full">
                <Skeleton level={loadingLevel} className="h-3 w-20 mb-3" />
                <Skeleton level={loadingLevel} className="h-5 w-full mb-2" />
                <Skeleton level={loadingLevel} className="h-5 w-3/4 mb-4" />
                <div className="mt-auto pt-2 space-y-2">
                  <Skeleton level={loadingLevel} className="h-3 w-24" />
                  <Skeleton level={loadingLevel} className="h-5 w-full rounded" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    );
  }
  if (error) return (
    <div className="py-8 border-t border-border mt-8 flex justify-center text-red-500">
      Error loading stories.
    </div>
  );
  if (!data || !data.data || data.data.length === 0) return (
    <div className="py-8 border-t border-border mt-8">
      <EmptyState>
        <EmptyIllustration
          icon={Newspaper}
          title="No stories available"
          description="Check back in a few minutes."
        />
      </EmptyState>
    </div>
  );

  const results = data.data;
  const isPersonalized = results[0].strategy === "behavioral_feed";
  const TitleIcon = isPersonalized ? Sparkles : TrendingUp;
  const titleText = isPersonalized ? "Recommended for You" : "Trending Now";

  // Map backend structure back to expected article fields
  const articles = results.map((r: any) => ({
    ...r.article,
    reason: r.reason
  }));

  const featured = articles[0];
  const compact = articles.slice(1, 7);
  
  const handleImpressionClick = (articleId: number, position: number) => {
    const sessionId = localStorage.getItem('tnt_session_id') || crypto.randomUUID();
    enqueue({
        event_id: crypto.randomUUID(),
        session_id: sessionId,
        article_id: articleId,
        event_type: "recommendation_click",
        event_version: "v1",
        occurred_at: new Date().toISOString(),
        metadata_payload: { position, strategy: results[position].strategy },
        source: "RECOMMENDATION_FEED"
    });
  };

  return (
    <section className="py-8 border-t border-border mt-8">
      <Reveal>
        <div className="flex items-center gap-3 mb-8">
          <div className="p-2 bg-primary/10 rounded-lg">
            <TitleIcon className="w-5 h-5 text-primary" />
          </div>
          <h2 className="text-2xl font-sans font-bold tracking-tight">{titleText}</h2>
        </div>
      </Reveal>

      <StaggerContainer className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Featured Card */}
        <StaggerItem className="lg:col-span-5 relative group">
          <Link href={`/articles/${featured.slug}`} onClick={() => handleImpressionClick(featured.id, 0)} className="block h-full border border-border bg-card overflow-hidden hover:border-primary/50 transition-colors">
            <ArticleThumbnail
              article={featured}
              className="aspect-video w-full"
              imgClassName="object-cover transition-transform duration-700 group-hover:scale-105"
              sizes="(max-width: 1024px) 100vw, 40vw"
            />
            <div className="p-6">
              <div className="flex items-center gap-3 text-[10px] font-mono uppercase tracking-wider text-primary mb-3">
                <span>{featured.source_name || featured.source}</span>
              </div>
              <h3 className="text-2xl font-serif font-bold text-foreground mb-3 leading-snug group-hover:text-primary transition-colors">
                {featured.title}
              </h3>
              <p className="text-muted-foreground text-sm line-clamp-3 mb-4">
                {featured.summary}
              </p>
              {featured.reason && (
                <div className="flex items-center gap-2 mt-auto p-2 bg-muted/50 rounded text-xs text-muted-foreground">
                  <Eye className="w-3.5 h-3.5 text-primary/70" />
                  <span>{featured.reason.message}</span>
                </div>
              )}
            </div>
          </Link>
        </StaggerItem>

        {/* Compact Cards */}
        <StaggerContainer className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-4">
          {compact.map((article: any, idx: number) => (
            <StaggerItem key={article.id}>
              <Link href={`/articles/${article.slug}`} onClick={() => handleImpressionClick(article.id, idx + 1)} className="group flex flex-col p-4 border border-border bg-card hover:border-primary/50 transition-colors h-full">
                <div className="flex items-center gap-2 text-[10px] font-mono uppercase tracking-wider text-muted-foreground mb-2">
                  <span className="text-primary">{article.source_name || article.source}</span>
                </div>
                <h4 className="font-serif font-bold text-base leading-snug group-hover:text-primary transition-colors mb-2">
                  {article.title}
                </h4>
                <div className="mt-auto flex flex-col gap-2 pt-2">
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <Clock className="w-3.5 h-3.5" />
                    <span suppressHydrationWarning>{article.published_at ? new Date(article.published_at).toLocaleDateString('en-US', { timeZone: 'UTC' }) : ''}</span>
                  </div>
                  {article.reason && (
                    <div className="text-[10px] bg-muted/50 p-1.5 rounded line-clamp-1 text-muted-foreground flex items-center gap-1.5">
                      <Eye className="w-3 h-3 text-primary/70" />
                      {article.reason.message}
                    </div>
                  )}
                </div>
              </Link>
            </StaggerItem>
          ))}
        </StaggerContainer>
      </StaggerContainer>
    </section>
  );
}
