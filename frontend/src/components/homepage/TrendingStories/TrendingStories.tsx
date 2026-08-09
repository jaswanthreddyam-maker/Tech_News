"use client";

import { useTrending } from "@/components/hooks/articles/useArticles";
import { useOfflineQueue } from "@/components/reading/tracker/useOfflineQueue";
import { Sparkles, TrendingUp } from "lucide-react";
import { useMemo, useRef, useState, useEffect } from "react";
import { m, useReducedMotion } from "framer-motion";
import { FeedArticle, FeedResponseItem } from "./types";
import { FeaturedStory } from "./FeaturedStory";
import { StoryTile } from "./StoryTile";
import { StorySkeleton } from "./StorySkeleton";
import { TRENDING_LAYOUT } from "./constants";
import { usePhysicalRig } from "./usePhysicalRig";
import { validateCanonicalArticles } from "@/domains/article/validator";
import {
  normalizeArticle,
  partitionFeed,
} from "./helpers";

import { useQueryClient } from "@tanstack/react-query";

/**
 * TrendingStories — Clean Architectural Orchestrator (v3.2 Direct 3D Matrix Motion)
 */
export function TrendingStories() {
  const queryClient = useQueryClient();
  const gridRef = usePhysicalRig<HTMLDivElement>();
  const { enqueue } = useOfflineQueue();
  
  const trendingQuery = useTrending();
  
  const data = trendingQuery.data;
  const isLoading = trendingQuery.isLoading;
  const error = trendingQuery.isError;

  // Animation Refs & Hooks
  const sectionRef = useRef<HTMLElement>(null);
  const [isInView, setIsInView] = useState(false);
  const shouldReduceMotion = useReducedMotion();

  useEffect(() => {
    if (isLoading || isInView) return;

    const section = sectionRef.current;
    if (!section) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;

        setIsInView(true);
        observer.disconnect();
      },
      { threshold: 0.15 } // Ensure 15% visibility triggers the cascade
    );
    
    observer.observe(section);
    return () => observer.disconnect();
  }, [isLoading, isInView]);

  // Listen to SSE events for thumbnail updates
  useEffect(() => {
    const sseUrl = "/api/v1/events/stream";
    const es = new EventSource(sseUrl);

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        // If the event indicates a thumbnail was updated, invalidate trending cache
        if (data && data.msg && data.msg.includes("thumbnail updated")) {
          queryClient.invalidateQueries({ queryKey: ["articles", "trending"] });
        }
      } catch (e) {
        // Ignore parse errors
      }
    };

    es.onerror = () => {
      // Allow EventSource's native reconnect behavior instead of hard closing.
      // E.g., don't do es.close();
    };

    return () => es.close();
  }, [queryClient]);

  // Removed transformTemplate: Framer Motion no longer touches transform property directly.

  const getCardDelay = (idx: number, isFeatured: boolean) => {
    if (isFeatured) return 0;
    // Custom stagger sequence for compact cards
    if (idx === 1) return 1;
    if (idx === 0) return 2;
    if (idx === 3) return 3;
    if (idx === 2) return 4;
    if (idx === 5) return 5;
    if (idx === 4) return 6;
    return idx + 1;
  };

  const getAnimationProps = (idx: number, isFeatured: boolean): any => {
    if (shouldReduceMotion) return {};
    
    return {
      initial: {
        "--reveal-ry": "-150deg",
        "--reveal-z": "-40px",
        opacity: 0.95,
        filter: "brightness(0.7)",
      },
      animate: isInView ? {
        "--reveal-ry": "0deg",
        "--reveal-z": "0px",
        opacity: 1,
        filter: "brightness(1)",
      } : undefined,
      transition: {
        duration: 1.1,
        delay: getCardDelay(idx, isFeatured) * 0.09, // 90ms delay between cascades
        ease: [0.22, 1, 0.36, 1] as const, // cinematic cubic-bezier
      },
    };
  };


  // Memoized Feed Transformer & Partitioning
  const { featured, compact, isPersonalized, titleText } = useMemo(() => {
    const rawResults: FeedResponseItem[] = Array.isArray(data)
      ? data
      : (data as any)?.data || [];

    if (!rawResults || rawResults.length === 0) {
      return {
        featured: null,
        compact: [],
        isPersonalized: false,
        titleText: "Trending Now",
      };
    }

    const title = "Trending Now";
    const articles: FeedArticle[] = rawResults.map(normalizeArticle);

    if (process.env.NODE_ENV === "development") {
      validateCanonicalArticles(articles as any);
    }

    const { featured: feat, compact: comp } = partitionFeed(articles);

    return {
      featured: feat,
      compact: comp,
      isPersonalized: false,
      titleText: title,
    };
  }, [data]);

  if (isLoading) {
    return <StorySkeleton />;
  }

  if (error) {
    return null;
  }

  if (!featured && compact.length === 0) return null;

  const TitleIcon = isPersonalized ? Sparkles : TrendingUp;

  const trackRecommendationClick = (articleId: number, position: number) => {
    const sessionId =
      localStorage.getItem("tnt_session_id") || crypto.randomUUID();
    enqueue({
      event_id: crypto.randomUUID(),
      session_id: sessionId,
      article_id: articleId,
      event_type: "recommendation_click",
      event_version: "v1",
      occurred_at: new Date().toISOString(),
      metadata_payload: {
        position,
        strategy: isPersonalized ? "behavioral_feed" : "trending",
      },
      source: "RECOMMENDATION_FEED",
    });
  };

  return (
    <section ref={sectionRef} className="TrendingWall py-8 my-6 w-full">
      {/* Editorial Section Header */}
      <div className="flex items-center gap-3 mb-9">
        <div className="p-2 bg-primary/10 rounded-xl">
          <TitleIcon className="w-4 h-4 text-primary" />
        </div>
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-foreground">
            {titleText}
          </h2>
          <p className="text-xs font-mono text-muted-foreground/80 tracking-wide mt-0.5">
            Stories gaining momentum across AI, software, hardware and startups.
          </p>
        </div>
      </div>

      {/* Perspective Container (1000px camera perspective) */}
      <div
        className="PerspectiveRig w-full mx-auto"
        style={{
          maxWidth: `${TRENDING_LAYOUT.MAX_WIDTH}px`,
          perspective: "1800px",
        }}
      >
        {/* Exhibition Grid Layout (Directly rotated by gridRef in 3D) */}
        <div
          ref={gridRef}
          className="ExhibitionGrid grid grid-cols-1 lg:grid-cols-12 gap-6 w-full mx-auto items-stretch"
          style={{
            transformStyle: "preserve-3d",
          }}
        >
          {/* Featured Story (5 cols desktop) */}
          {featured && (
            <m.div 
              className="ExhibitionItem lg:col-span-5 flex [transform:translateZ(var(--reveal-z,0px))_rotateY(var(--reveal-ry,0deg))]" 
              style={{ transformStyle: "preserve-3d" }}
              {...getAnimationProps(0, true)}
            >
              <FeaturedStory
                article={featured}
                onClick={() => trackRecommendationClick(featured.id, 0)}
              />
            </m.div>
          )}

          {/* Story Tiles Grid (7 cols desktop, 2x3 grid) */}
          <div className="ExhibitionItem lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-6 auto-rows-fr" style={{ transformStyle: "preserve-3d" }}>
            {compact.map((article: FeedArticle, idx: number) => (
              <m.div
                key={article.slug || (article.id ? `id-${article.id}` : `tile-${idx}`)}
                className="w-full h-full flex [transform:translateZ(var(--reveal-z,0px))_rotateY(var(--reveal-ry,0deg))]"
                style={{ transformStyle: "preserve-3d" }}
                {...getAnimationProps(idx, false)}
              >
                <StoryTile
                  article={article}
                  onClick={() => trackRecommendationClick(article.id, idx + 1)}
                />
              </m.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
