"use client";

import { useBreaking, usePersonalizedFeed } from "@/components/hooks/articles/useArticles";
import { Skeleton } from "@/design-system/components/Skeleton";
import { useLoadingState } from "@/design-system/hooks/useLoadingState";
import { AnimatePresence, m } from "framer-motion";
import { Clock, Newspaper } from "lucide-react";
import { EmptyState, EmptyIllustration } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { useEffect, useState, useRef, useMemo } from "react";
import { Article } from "@/lib/api/types";
import { ArticleLink } from "@/domains/article/ArticleLink";
import { getApiBaseUrl } from "@/lib/api/getApiBaseUrl";

/** Apple / Arc Signature Easing Curve */
const EASE_CUBIC = [0.16, 1, 0.3, 1] as const;

/** Extract contextual topic label for personalized feed items */
function getContextTopic(article: any): string | null {
  if (article.primary_topics && Array.isArray(article.primary_topics) && article.primary_topics.length > 0) {
    return article.primary_topics[0].replace(/[-_]/g, " ").toUpperCase();
  }
  if (article.primaryTopics && Array.isArray(article.primaryTopics) && article.primaryTopics.length > 0) {
    return article.primaryTopics[0].replace(/[-_]/g, " ").toUpperCase();
  }
  if (article.topics && Array.isArray(article.topics) && article.topics.length > 0) {
    const t = typeof article.topics[0] === "string" ? article.topics[0] : article.topics[0]?.name;
    if (t) return t.replace(/[-_]/g, " ").toUpperCase();
  }
  if (typeof article.category === "string" && article.category.trim()) {
    return article.category.replace(/[-_]/g, " ").toUpperCase();
  }
  if (typeof article.category === "object" && article.category?.name) {
    return article.category.name.replace(/[-_]/g, " ").toUpperCase();
  }
  if (article.primary_topic) {
    return String(article.primary_topic).replace(/[-_]/g, " ").toUpperCase();
  }
  return null;
}

/** Helper to format published time safely */
function formatTime(dateStr?: string | null): string {
  if (!dateStr) return "TODAY";
  try {
    const d = new Date(dateStr);
    return isNaN(d.getTime())
      ? "TODAY"
      : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "TODAY";
  }
}

export function BreakingNews() {
  const [activeTab, setActiveTab] = useState<"latest" | "following">("latest");

  // Query 1: Chronological Editorial Stream (with SSE live additions)
  const { data: breakingData, isLoading: isLatestLoading, error: latestError } = useBreaking();
  const [liveArticles, setLiveArticles] = useState<Article[]>([]);
  const bufferRef = useRef<Article[]>([]);

  // Query 2: Personalized Feed Stream (Topics/Sources followed & behavioral affinities)
  const { data: feedData, isLoading: isFeedLoading, error: feedError } = usePersonalizedFeed();

  // Seed liveArticles with initial query data
  useEffect(() => {
    if (breakingData?.data) {
      setLiveArticles(breakingData.data.slice(0, 10));
    }
  }, [breakingData]);

  // Connect to SSE for real-time injections in Latest mode
  useEffect(() => {
    const sseUrl = getApiBaseUrl() + "/events/stream";
    const eventSource = new EventSource(sseUrl);

    eventSource.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.agent === "INGESTION" && payload.meta) {
          const newArt = payload.meta as Article;
          if (!bufferRef.current.some((a) => a.id === newArt.id)) {
            bufferRef.current.push(newArt);
          }
        }
      } catch {
        // ignore parse errors
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
    };

    const bufferMs = Number(process.env.NEXT_PUBLIC_BREAKING_BUFFER_MS || 2000);
    const intervalId = setInterval(() => {
      if (bufferRef.current.length > 0) {
        setLiveArticles((prev) => {
          const combined = [...bufferRef.current, ...prev];
          const unique = Array.from(new Map(combined.map((item) => [item.id, item])).values());
          return unique.slice(0, 10);
        });
        bufferRef.current = [];
      }
    }, bufferMs);

    return () => {
      eventSource.close();
      clearInterval(intervalId);
    };
  }, []);

  // Normalize personalized following articles
  const followingArticles = useMemo(() => {
    if (!feedData?.data) return [];
    // Extract articles from FeedItemResponse ({ article, reasoning_metadata }) or direct Article objects
    return feedData.data.map((item: any) => item.article || item).slice(0, 10);
  }, [feedData]);

  const currentArticles = activeTab === "latest" ? liveArticles : followingArticles;
  const isCurrentLoading = activeTab === "latest" ? isLatestLoading : isFeedLoading;
  const currentError = activeTab === "latest" ? latestError : feedError;
  const loadingLevel = useLoadingState(isCurrentLoading);

  return (
    <m.div 
      id="latest-stories"
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.15 }}
      transition={{ duration: 0.8, ease: EASE_CUBIC }}
      className="LatestStoriesSection w-full max-w-4xl mx-auto overflow-hidden py-8 scroll-mt-24" 
      aria-live="polite"
    >
      {/* Section Header with Dynamic Copy */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8 pb-6 border-b border-white/10">
        <div className="space-y-1">
          <h2 className="text-2xl sm:text-3xl font-sans font-bold tracking-tight text-foreground">
            {activeTab === "latest" ? "Latest Stories" : "Your Feed"}
          </h2>
          <p className="text-xs font-mono text-muted-foreground/70">
            {activeTab === "latest"
              ? "The newest stories from across every category."
              : "The latest stories from the topics and sources you follow."}
          </p>
        </div>
        
        {/* Editorial Navigation Tabs */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-white/[0.04] border border-white/10 self-start sm:self-auto">
          <button
            type="button"
            id="tab-latest"
            onClick={() => setActiveTab("latest")}
            className={`px-3.5 py-1.5 text-xs font-mono font-semibold rounded-lg transition-all cursor-pointer ${
              activeTab === "latest"
                ? "bg-white/10 text-foreground border border-white/20 shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Latest
          </button>
          <button
            type="button"
            id="tab-following"
            onClick={() => setActiveTab("following")}
            className={`px-3.5 py-1.5 text-xs font-mono font-semibold rounded-lg transition-all cursor-pointer ${
              activeTab === "following"
                ? "bg-white/10 text-foreground border border-white/20 shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Following
          </button>
        </div>
      </div>

      {/* Content Area with Smooth Subtle Transition */}
      {isCurrentLoading ? (
        <div className="flex flex-col gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="flex flex-col gap-2 pb-6 border-b border-white/10">
              <Skeleton level={loadingLevel} className="h-4 w-24" />
              <Skeleton level={loadingLevel} className="h-7 w-3/4" />
              <Skeleton level={loadingLevel} className="h-3.5 w-36" />
            </div>
          ))}
        </div>
      ) : currentError ? (
        <ErrorState title="Unable to load stories" description="Could not fetch the editorial feed." />
      ) : currentArticles.length === 0 ? (
        <EmptyState size="sm">
          <EmptyIllustration
            icon={Newspaper}
            title={activeTab === "latest" ? "No stories available" : "No followed stories yet"}
            description={
              activeTab === "latest"
                ? "Check back shortly for new reporting."
                : "Follow topics or entities across stories to customize your personal feed."
            }
          />
        </EmptyState>
      ) : (
        <div className="flex flex-col divide-y divide-white/[0.08]">
          <AnimatePresence mode="wait">
            <m.div
              key={activeTab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.25, ease: EASE_CUBIC }}
              className="flex flex-col divide-y divide-white/[0.08]"
            >
              {currentArticles.map((article: any, index: number) => {
                const contextTopic = activeTab === "following" ? getContextTopic(article) : null;
                const sourceName = article.source || article.source_name || "TECH NEWS TODAY";
                const readTime = article.readTime || article.read_time || article.reading_time || 4;

                return (
                  <div
                    key={article.id || index}
                    className="group py-6 first:pt-2"
                  >
                    <ArticleLink
                      article={article}
                      section={activeTab === "latest" ? "LatestStories" : "YourFeed"}
                      position={index}
                      className="block w-full"
                    >
                      {/* Contextual Header */}
                      {activeTab === "following" ? (
                        <div className="flex flex-col gap-1 mb-2">
                          {contextTopic && (
                            <span className="text-[10px] font-mono font-bold tracking-widest uppercase text-primary/90">
                              {contextTopic}
                            </span>
                          )}
                          <span className="text-[11px] font-mono font-bold uppercase tracking-widest text-muted-foreground/80 group-hover:text-primary transition-colors">
                            {sourceName}
                          </span>
                        </div>
                      ) : (
                        /* Publisher Tag (Latest) */
                        <div className="text-[11px] font-mono font-bold uppercase tracking-widest text-muted-foreground/80 mb-2 group-hover:text-primary transition-colors">
                          {sourceName}
                        </div>
                      )}

                      {/* Article Headline */}
                      <h4 className="font-sans text-xl sm:text-2xl font-medium leading-[1.3] tracking-tight text-foreground/95 group-hover:text-primary transition-colors mb-3 max-w-3xl">
                        {article.title}
                      </h4>

                      {/* Metadata Footer */}
                      <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground/60">
                        <Clock className="w-3.5 h-3.5 text-muted-foreground/50" />
                        <span suppressHydrationWarning>{formatTime(article.published_at)}</span>
                        <span>•</span>
                        <span>{readTime} min read</span>
                      </div>
                    </ArticleLink>
                  </div>
                );
              })}
            </m.div>
          </AnimatePresence>
        </div>
      )}
    </m.div>
  );
}

