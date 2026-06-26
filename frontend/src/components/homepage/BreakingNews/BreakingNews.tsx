"use client";

import { useBreaking } from "@/components/hooks/articles/useArticles";
import { Skeleton } from "@/design-system/components/Skeleton";
import { useLoadingState } from "@/design-system/hooks/useLoadingState";
import { AnimatePresence } from "framer-motion";
import { Radio, Clock, Newspaper } from "lucide-react";
import { EmptyState, EmptyIllustration } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import Link from "next/link";
import { useEffect, useState, useRef } from "react";
import { Article } from "@/lib/api/types";
import { Reveal, StaggerContainer, StaggerItem } from "@/components/animations";

export function BreakingNews() {
  const { data, isLoading, error } = useBreaking();
  const [liveArticles, setLiveArticles] = useState<Article[]>([]);
  const bufferRef = useRef<Article[]>([]);

  // Seed with initial query data
  useEffect(() => {
    if (data?.data) {
      setLiveArticles(data.data.slice(0, 3));
    }
  }, [data]);

  // Connect to SSE for real-time injections with buffering
  useEffect(() => {
    const sseUrl = (process.env.NEXT_PUBLIC_API_URL || "/api/v1") + "/events/stream";
    const eventSource = new EventSource(sseUrl);

    eventSource.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.agent === "INGESTION" && payload.meta) {
          const newArt = payload.meta as Article;
          // Push to buffer instead of state immediately
          if (!bufferRef.current.some((a) => a.id === newArt.id)) {
            bufferRef.current.push(newArt);
          }
        }
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      } catch (e) {
        // ignore parse errors
      }
    };

    const bufferMs = Number(process.env.NEXT_PUBLIC_BREAKING_BUFFER_MS || 2000);
    const intervalId = setInterval(() => {
      if (bufferRef.current.length > 0) {
        setLiveArticles((prev) => {
          const combined = [...bufferRef.current, ...prev];
          const unique = Array.from(new Map(combined.map(item => [item.id, item])).values());
          return unique.slice(0, 3);
        });
        bufferRef.current = []; // flush buffer
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
      <div className="w-full overflow-hidden">
        <div className="flex items-center gap-4 mb-4">
          <Skeleton level={loadingLevel} className="h-8 w-32 rounded-full" />
          <div className="h-[1px] flex-1 bg-border" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-card border border-border p-4 relative overflow-hidden h-[100px] flex flex-col justify-center">
              <div className="absolute top-0 left-0 w-1 h-full bg-border/50" />
              <Skeleton level={loadingLevel} className="h-4 w-full mb-2" />
              <Skeleton level={loadingLevel} className="h-4 w-3/4 mb-3" />
              <div className="flex items-center gap-3">
                <Skeleton level={loadingLevel} className="h-3 w-16" />
                <Skeleton level={loadingLevel} className="h-3 w-12" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }
  if (error) {
    return <ErrorState title="Breaking News Error" description="Could not load live updates." />;
  }
  
  if (liveArticles.length === 0) {
    return (
      <EmptyState size="sm">
        <EmptyIllustration
          icon={Newspaper}
          title="No live updates"
          description="Check back later for breaking news."
        />
      </EmptyState>
    );
  }

  return (
    <div className="w-full overflow-hidden" aria-live="polite">
      <Reveal>
        <div className="flex items-center gap-4 mb-4">
          <div className="flex items-center gap-2 text-red-500 font-mono text-xs font-bold uppercase tracking-widest bg-red-500/10 px-3 py-1.5 rounded-full border border-red-500/20">
            <Radio className="w-3.5 h-3.5 animate-pulse" />
            Live Updates
          </div>
          <div className="h-[1px] flex-1 bg-border" />
        </div>
      </Reveal>

      <StaggerContainer className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <AnimatePresence mode="popLayout">
          {liveArticles.map((article) => (
            <StaggerItem
              key={article.id}
              exit={{ opacity: 0, scale: 0.95 }}
              className="group bg-card border border-border p-4 hover:border-primary/50 transition-colors relative overflow-hidden h-[100px]"
            >
              <div className="absolute top-0 left-0 w-1 h-full bg-red-500/50" />
              <Link href={`/articles/${article.slug}`} className="block">
                <h4 className="font-sans font-bold text-sm text-foreground line-clamp-2 mb-2 group-hover:text-primary transition-colors">
                  {article.title}
                </h4>
                <div className="flex items-center gap-3 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                  <span>{article.source}</span>
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {new Date(article.published_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              </Link>
            </StaggerItem>
          ))}
        </AnimatePresence>
      </StaggerContainer>
    </div>
  );
}
