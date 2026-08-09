"use client";

import React, { useState, useEffect, useCallback } from "react";
import { m } from "framer-motion";
import { MotionScales } from "@/design-system/motion/tokens";
import { ArticleThumbnail } from "@/components/common/ArticleThumbnail";
import { formatDistanceToNow } from "date-fns";
import { RecommendationReasonBadges } from "@/components/recommendation/RecommendationReasonBadges";
import { useArticleTransition } from "@/components/layout/RouteTransitionProvider";
import { ArticleLink } from "@/domains/article/ArticleLink";
import { resolve as resolveArticleMedia } from "@/domains/article/media/resolve";

export interface StoryCardProps {
  article: {
    id: number;
    slug: string;
    title: string;
    hero_image?: string | null;
    image_url?: string | null;
    thumbnail_local?: string | null;
    thumbnail_url?: string | null;
    source_name?: string | null;
    source?: string | null;
    published_at?: string | null;
    category?: string | null;
  };
  recommendation?: {
    reasons?: Array<{
      type: "similarity" | "trending" | "credible" | "topic" | "freshness";
      score?: number;
      label: string;
    }>;
  };
  className?: string;
}

export function StoryCard({ article, recommendation, className = "" }: StoryCardProps) {
  const [isMounted, setIsMounted] = useState(false);
  const { setTransitionData } = useArticleTransition();
  const sourceName = article.source_name || article.source || "Unknown Source";

  useEffect(() => {
    setIsMounted(true);
  }, []);

  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
      const media = resolveArticleMedia(article as any);
      setTransitionData({
        cardRect: rect,
        cardImageSrc: media.url,
        cardTitle: article.title || null,
      });
    },
    [article, setTransitionData]
  );

  const CardContent = (
    <>
      <ArticleThumbnail
        article={article}
        className="relative aspect-video w-full"
        imgClassName="object-cover group-hover:scale-105 transition-transform duration-500"
        sizes="(max-width: 768px) 100vw, 33vw"
      />
      
      <div className="p-4 flex flex-col flex-grow">
        {recommendation?.reasons && (
          <RecommendationReasonBadges reasons={recommendation.reasons} className="mb-3" />
        )}
        
        {article.category && !recommendation?.reasons && (
          <div className="mb-2 text-[10px] font-mono uppercase tracking-wider text-primary">
            {article.category}
          </div>
        )}

        <h4 className="font-bold text-lg mb-2 line-clamp-2 group-hover:text-primary transition-colors">
          {article.title}
        </h4>
        
        <div className="mt-auto flex items-center justify-between text-xs text-muted-foreground font-mono uppercase tracking-wider pt-2 border-t border-border/20">
          <span className="truncate mr-2">{sourceName}</span>
          <span className="shrink-0">
            {article.published_at ? formatDistanceToNow(new Date(article.published_at), { addSuffix: true }) : ''}
          </span>
        </div>
      </div>
    </>
  );

  return (
    <ArticleLink 
      article={article} 
      onClick={handleClick}
      className={`group block h-full ${className}`}
    >
      {!isMounted ? (
        <div className="flex flex-col h-full bg-card rounded-xl border border-border/50 overflow-hidden hover:border-primary/50 transition-colors">
          {CardContent}
        </div>
      ) : (
        <m.div
          whileHover={{ scale: MotionScales.card }}
          whileTap={{ scale: MotionScales.tap }}
          className="flex flex-col h-full bg-card rounded-xl border border-border/50 overflow-hidden hover:border-primary/50 transition-colors"
        >
          {CardContent}
        </m.div>
      )}
    </ArticleLink>
  );
}
