"use client";

import React, { useState, useEffect, useRef } from "react";
import { AnimatePresence, m } from "framer-motion";
import { Clock, Plus, Check, Settings2, SlidersHorizontal } from "lucide-react";
import { useBreaking } from "@/components/hooks/articles/useArticles";
import { useSourceFollow } from "@/hooks/useSourceFollow";
import { SourceSelectorModal, FALLBACK_SOURCES } from "@/components/sources/SourceSelectorModal";
import { Skeleton } from "@/design-system/components/Skeleton";
import { useLoadingState } from "@/design-system/hooks/useLoadingState";
import { Article } from "@/lib/api/types";
import { ArticleLink } from "@/domains/article/ArticleLink";
import { getApiBaseUrl } from "@/lib/api/getApiBaseUrl";

/** Apple / Arc Signature Easing Curve */
const EASE_CUBIC = [0.16, 1, 0.3, 1] as const;

/** Format published time safely */
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
  const [activeTab, setActiveTab] = useState<"latest" | "following">("following");
  const [isSourceModalOpen, setIsSourceModalOpen] = useState(false);

  // 1. Latest Chronological Stream (with real-time SSE additions)
  const { data: breakingData, isLoading: isLatestLoading, error: latestError } = useBreaking();
  const [liveArticles, setLiveArticles] = useState<Article[]>([]);
  const bufferRef = useRef<Article[]>([]);

  // 2. Personal Source Following Stream
  const {
    sources,
    followedSources,
    followedCount,
    feedArticles,
    isFeedLoading,
    feedError,
    toggleFollow,
    isToggling,
  } = useSourceFollow();

  // All available sources (using default fallbacks if API is loading or network is slow)
  const allAvailableSources = sources && sources.length > 0 ? sources : FALLBACK_SOURCES;

  // Suggested sources for onboarding when 0 sources are followed
  const suggestedSources = allAvailableSources
    .filter((s) => s.category === "official")
    .slice(0, 4);

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
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-6 pb-6 border-b border-white/10">
        <div className="space-y-1">
          <h2 className="text-2xl sm:text-3xl font-sans font-bold tracking-tight text-foreground">
            {activeTab === "latest" ? "Latest Stories" : "Your Feed"}
          </h2>
          <p className="text-xs font-mono text-muted-foreground/70">
            {activeTab === "latest"
              ? "The newest stories from across every category."
              : "The latest stories from the sources you follow."}
          </p>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-white/[0.04] border border-white/10 self-start sm:self-auto">
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
            Following ({followedCount})
          </button>
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
            Explore All
          </button>
        </div>
      </div>

      {/* Following Feed Source Subscription Controls */}
      {activeTab === "following" && (
        <div className="flex flex-wrap items-center justify-between gap-2.5 mb-8 p-3 sm:px-4 rounded-xl bg-white/[0.02] border border-white/10">
          <div className="flex flex-wrap items-center gap-1.5">
            {followedSources.length > 0 ? (
              followedSources.map((source) => (
                <button
                  key={source.slug}
                  type="button"
                  onClick={() => setIsSourceModalOpen(true)}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/[0.06] hover:bg-white/10 text-xs font-mono font-medium text-foreground border border-white/10 transition-all cursor-pointer group"
                  title="Click to manage source"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  <span>{source.name.replace(/ Blog| News| Newsroom| AI Blog/g, "")}</span>
                </button>
              ))
            ) : (
              <span className="text-xs font-mono text-muted-foreground/70">
                No sources followed yet.
              </span>
            )}
          </div>

          <button
            type="button"
            id="btn-manage-sources"
            onClick={() => setIsSourceModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-xs font-mono font-semibold text-foreground border border-white/10 transition-all cursor-pointer"
          >
            <SlidersHorizontal className="w-3.5 h-3.5 text-primary" />
            <span>{followedSources.length === 0 ? "+ Add sources" : "Manage Sources →"}</span>
          </button>
        </div>
      )}

      {/* Content Area */}
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
        <div className="py-12 text-center space-y-3 bg-white/[0.02] border border-white/10 rounded-2xl p-6">
          <p className="text-sm font-sans font-medium text-foreground">Unable to load feed</p>
          <p className="text-xs font-mono text-muted-foreground">Please refresh or check your connection.</p>
        </div>
      ) : activeTab === "following" && followedCount === 0 ? (
        /* Case A Empty State: 0 Sources Followed */
        <div className="flex flex-col items-center justify-center p-8 sm:p-12 text-center rounded-2xl bg-white/[0.02] border border-white/10 space-y-6">
          <div className="space-y-2 max-w-md">
            <h3 className="text-lg sm:xl font-sans font-bold text-foreground">
              Stay close to the companies shaping technology
            </h3>
            <p className="text-xs font-mono text-muted-foreground/80 leading-relaxed">
              Follow official newsrooms and editorial publishers to receive direct updates in your feed.
            </p>
          </div>

          {/* Quick-Follow Suggested Sources */}
          <div className="w-full max-w-lg grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-left">
            {suggestedSources.map((source) => (
              <div
                key={source.slug}
                className="flex items-center justify-between p-3 rounded-xl bg-white/[0.04] border border-white/10 hover:border-white/20 transition-all"
              >
                <div className="flex flex-col">
                  <span className="text-xs font-sans font-semibold text-foreground">
                    {source.name}
                  </span>
                  <span className="text-[10px] font-mono text-muted-foreground/70">
                    Official Newsroom
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => toggleFollow(source.slug)}
                  disabled={isToggling}
                  className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-white/10 hover:bg-white/20 text-[11px] font-mono font-semibold text-foreground transition-all cursor-pointer"
                >
                  <Plus className="w-3 h-3" />
                  <span>Follow</span>
                </button>
              </div>
            ))}
          </div>

          <button
            type="button"
            onClick={() => setIsSourceModalOpen(true)}
            className="text-xs font-mono font-semibold text-primary hover:underline cursor-pointer"
          >
            Browse all sources →
          </button>
        </div>
      ) : activeTab === "following" && feedArticles.length === 0 ? (
        /* Case B Empty State: Sources Followed, but 0 Articles */
        <div className="flex flex-col items-center justify-center p-8 sm:p-12 text-center rounded-2xl bg-white/[0.02] border border-white/10 space-y-4">
          <div className="space-y-1.5 max-w-md">
            <h3 className="text-lg font-sans font-bold text-foreground">
              Nothing new from your sources
            </h3>
            <p className="text-xs font-mono text-muted-foreground/80 leading-relaxed">
              Stories published by{" "}
              {followedSources.map((s) => s.name.replace(/ Blog| News| Newsroom| AI Blog/g, "")).join(", ")}{" "}
              will appear here as soon as they release new articles.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setIsSourceModalOpen(true)}
            className="px-3.5 py-1.5 rounded-xl bg-white/10 hover:bg-white/15 text-xs font-mono font-semibold text-foreground border border-white/10 transition-all cursor-pointer"
          >
            Follow more sources →
          </button>
        </div>
      ) : (
        /* Article Stream */
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
              {(activeTab === "latest" ? liveArticles : feedArticles).map(
                (article: any, index: number) => {
                  const sourceName = article.source || article.source_name || "TECH NEWS TODAY";
                  const readTime =
                    article.readTime || article.read_time || article.reading_time || 4;

                  return (
                    <div key={article.id || index} className="group py-6 first:pt-2">
                      <ArticleLink
                        article={article}
                        section={activeTab === "latest" ? "LatestStories" : "YourFeed"}
                        position={index}
                        className="block w-full"
                      >
                        {/* Publisher Tag */}
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-[11px] font-mono font-bold uppercase tracking-widest text-muted-foreground/80 group-hover:text-primary transition-colors">
                            {sourceName}
                          </span>
                        </div>

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
                }
              )}
            </m.div>
          </AnimatePresence>
        </div>
      )}

      {/* Source Selection & Management Modal */}
      <SourceSelectorModal
        isOpen={isSourceModalOpen}
        onClose={() => setIsSourceModalOpen(false)}
        sources={allAvailableSources}
        onToggleFollow={toggleFollow}
        isToggling={isToggling}
      />
    </m.div>
  );
}
