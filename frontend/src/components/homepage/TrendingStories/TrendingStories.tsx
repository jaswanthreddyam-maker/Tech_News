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
import { getApiBaseUrl } from "@/lib/api/getApiBaseUrl";

/**
 * TrendingStories — Clean Architectural Orchestrator (v3.3 Compositor-Friendly Transforms)
 *
 * PERF FIX v3.3:
 * Replaced CSS variable animation (--reveal-ry / --reveal-z) with direct Framer Motion
 * transform properties (rotateY, z). CSS variable animations force a CSSOM style
 * recalculation pass on the main thread every frame for all animated children, completely
 * bypassing the GPU compositor. Direct transform properties allow Framer Motion to hand
 * the animation off to the compositor thread via the Web Animations API.
 *
 * Before: 7 cards × 2 CSS vars = 14 main-thread style recalculations per frame (~60/s)
 * After:  compositor-owned transform, zero main-thread work per frame during animation
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
      { threshold: 0.15 }
    );

    observer.observe(section);
    return () => observer.disconnect();
  }, [isLoading, isInView]);

  // Listen to SSE events for thumbnail updates
  useEffect(() => {
    const sseUrl = getApiBaseUrl() + "/events/stream";
    const es = new EventSource(sseUrl);

    es.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        if (parsed && parsed.msg && parsed.msg.includes("thumbnail updated")) {
          queryClient.invalidateQueries({ queryKey: ["articles", "trending"] });
        }
      } catch {
        // Ignore parse errors
      }
    };

    es.onerror = () => {
      // Allow EventSource's native reconnect behavior
    };

    return () => es.close();
  }, [queryClient]);

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

  /**
   * PERF v3.3: Use direct transform properties (rotateY, z, opacity) instead of
   * CSS custom properties (--reveal-ry, --reveal-z).
   *
   * WHY: Framer Motion can hand direct transform properties (translate, rotate, scale)
   * to the browser's compositor thread via the Web Animations API, bypassing main-thread
   * style recalculation entirely. CSS variable animation CANNOT use this path — the
   * browser must re-evaluate the variable through the CSSOM cascade on the main thread
   * on every animation frame, causing forced style recalculation across the entire
   * card subtree (7 cards × 2 properties = 14 recalculations per frame at 60fps).
   */
  const getAnimationProps = (idx: number, isFeatured: boolean): any => {
    if (shouldReduceMotion) return {};

    return {
      initial: {
        rotateY: -25,
        z: -30,
        opacity: 0,
        filter: "brightness(0.6)",
      },
      animate: isInView
        ? {
            rotateY: 0,
            z: 0,
            opacity: 1,
            filter: "brightness(1)",
          }
        : undefined,
      transition: {
        duration: 2.2,
        delay: getCardDelay(idx, isFeatured) * 0.14, // 140ms stagger — slower cascade
        ease: [0.16, 1, 0.3, 1] as const, // slow-motion cubic-bezier — long deceleration tail
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

      {/* Perspective Container (1800px camera perspective) */}
      <div
        className="PerspectiveRig w-full mx-auto"
        style={{
          maxWidth: `${TRENDING_LAYOUT.MAX_WIDTH}px`,
          perspective: "1800px",
        }}
      >
        {/*
         * ExhibitionGrid — single element rotated by usePhysicalRig on mousemove.
         * usePhysicalRig writes transform directly via el.style.transform using a
         * requestAnimationFrame loop with lerp. No React state is touched on mouse move.
         * will-change is NOT applied here to avoid creating excess compositor layers.
         */}
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
              className="ExhibitionItem lg:col-span-5 flex"
              style={{ transformStyle: "preserve-3d" }}
              {...getAnimationProps(0, true)}
            >
              <FeaturedStory
                article={featured}
                onClick={() => trackRecommendationClick(featured.id, 0)}
              />
            </m.div>
          )}

          {/* Story Tiles Grid (7 cols desktop, 2×3 grid) */}
          <div
            className="ExhibitionItem lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-6 auto-rows-fr"
            style={{ transformStyle: "preserve-3d" }}
          >
            {compact.map((article: FeedArticle, idx: number) => (
              <m.div
                key={article.slug || (article.id ? `id-${article.id}` : `tile-${idx}`)}
                className="w-full h-full flex"
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
