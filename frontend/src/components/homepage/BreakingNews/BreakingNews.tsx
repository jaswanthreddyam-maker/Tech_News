"use client";

import { useBreaking } from "@/components/hooks/articles/useArticles";
import { Skeleton } from "@/design-system/components/Skeleton";
import { useLoadingState } from "@/design-system/hooks/useLoadingState";
import { AnimatePresence, m } from "framer-motion";
import { Clock, Newspaper, ArrowRight } from "lucide-react";
import { EmptyState, EmptyIllustration } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { useEffect, useState, useRef } from "react";
import { Article } from "@/lib/api/types";
import { ArticleLink } from "@/domains/article/ArticleLink";

/** Apple / Arc Signature Easing Curve */
const EASE_CUBIC = [0.16, 1, 0.3, 1] as const;

export function BreakingNews() {
  const { data, isLoading, error } = useBreaking();
  const [liveArticles, setLiveArticles] = useState<Article[]>([]);
  const [activeTab, setActiveTab] = useState<"latest" | "following">("latest");
  const bufferRef = useRef<Article[]>([]);

  // Seed with initial query data
  useEffect(() => {
    if (data?.data) {
      setLiveArticles(data.data.slice(0, 10));
    }
  }, [data]);

  // Connect to SSE for real-time injections
  useEffect(() => {
    const sseUrl = (process.env.NEXT_PUBLIC_API_URL || "/api/v1") + "/events/stream";
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
      } catch (e) {
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
          const unique = Array.from(new Map(combined.map(item => [item.id, item])).values());
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

  const loadingLevel = useLoadingState(isLoading);

  if (isLoading) {
    return (
      <div className="w-full max-w-4xl mx-auto overflow-hidden py-8">
        <Skeleton level={loadingLevel} className="h-8 w-56 mb-8 rounded-lg" />
        <div className="flex flex-col gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="flex flex-col gap-2 pb-6 border-b border-white/10">
              <Skeleton level={loadingLevel} className="h-4 w-24" />
              <Skeleton level={loadingLevel} className="h-7 w-3/4" />
              <Skeleton level={loadingLevel} className="h-3.5 w-36" />
            </div>
          ))}
        </div>
      </div>
    );
  }
  
  if (error) {
    return <ErrorState title="Unable to load stories" description="Could not fetch the latest editorial updates." />;
  }
  
  if (liveArticles.length === 0) {
    return (
      <EmptyState size="sm">
        <EmptyIllustration
          icon={Newspaper}
          title="No stories available"
          description="Check back shortly for new reporting."
        />
      </EmptyState>
    );
  }

  return (
    <m.div 
      initial={{ opacity: 0, y: 40 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.15 }}
      transition={{ duration: 0.9, ease: EASE_CUBIC }}
      className="w-full max-w-4xl mx-auto overflow-hidden py-8" 
      aria-live="polite"
    >
      {/* Section Header: Latest Stories */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8 pb-6 border-b border-white/10">
        <div className="space-y-1">
          <h2 className="text-2xl sm:text-3xl font-sans font-bold tracking-tight text-foreground">
            Latest Stories
          </h2>
          <p className="text-xs font-mono text-muted-foreground/70">
            The newest articles from across every category.
          </p>
        </div>
        
        {/* Editorial Navigation Tabs */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-white/[0.04] border border-white/10">
          <button
            type="button"
            onClick={() => setActiveTab('latest')}
            className={`px-3.5 py-1.5 text-xs font-mono font-semibold rounded-lg transition-all cursor-pointer ${
              activeTab === 'latest'
                ? "bg-white/10 text-foreground border border-white/20 shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Latest
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('following')}
            className={`px-3.5 py-1.5 text-xs font-mono font-semibold rounded-lg transition-all cursor-pointer ${
              activeTab === 'following'
                ? "bg-white/10 text-foreground border border-white/20 shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Following
          </button>
        </div>
      </div>

      {/* Editorial Story List */}
      <div className="flex flex-col divide-y divide-white/[0.08]">
        <AnimatePresence mode="popLayout">
          {liveArticles.map((article, index) => (
            <m.div
              key={article.id || index}
              layout
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.15 }}
              exit={{ opacity: 0, x: -10 }}
              transition={{ duration: 0.7, delay: index * 0.06, ease: EASE_CUBIC }}
              className="group py-6 first:pt-2"
            >
              <ArticleLink article={article} section="LatestStories" position={index} className="block w-full">
                
                {/* Publisher Tag */}
                <div className="text-[11px] font-mono font-bold uppercase tracking-widest text-muted-foreground/80 mb-2 group-hover:text-primary transition-colors">
                  {article.source || "TECH NEWS TODAY"}
                </div>

                {/* Article Headline */}
                <h4 className="font-sans text-xl sm:text-2xl font-medium leading-[1.3] tracking-tight text-foreground/95 group-hover:text-primary transition-colors mb-3 max-w-3xl">
                  {article.title}
                </h4>

                {/* Metadata Footer */}
                <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground/60">
                  <Clock className="w-3.5 h-3.5 text-muted-foreground/50" />
                  <span>{new Date(article.published_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  <span>•</span>
                  <span>{(article as any).readTime || 4} min read</span>
                </div>

              </ArticleLink>
            </m.div>
          ))}
        </AnimatePresence>
      </div>
    </m.div>
  );
}
