"use client";

import React, { useState } from "react";
import { Clock, ArrowRight } from "lucide-react";
import { ArticleThumbnail } from "@/components/common/ArticleThumbnail";
import { m } from "framer-motion";
import { MOTION_TOKENS } from "@/components/animations/motionTokens";
import { ArticleLink } from "@/domains/article/ArticleLink";
import { getPresentationForArticle } from "@/domains/article/presentation";
import { CardTopics, CardHeader } from "@/components/common/card/primitives";

interface FloatingEditorialPanelProps {
  article: any;
  index: number;
  isPrimary?: boolean;
}

export function FloatingEditorialPanel({ article, index, isPrimary = false }: FloatingEditorialPanelProps) {
  const [isHovered, setIsHovered] = useState(false);
  const presentation = getPresentationForArticle(article);

  // Asymmetric floating hierarchy (Base Z)
  const baseElevations = [14, 12, 10, 12];
  const baseZ = baseElevations[index % baseElevations.length];
  const activeZ = isHovered ? 28 : baseZ;

  // Staggered breathing delays for weightless asynchronous floating
  const phaseDelay = (index % 4) * MOTION_TOKENS.STAGGER_SMALL * 8;

  return (
    <m.div
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      initial={{ opacity: 0, y: MOTION_TOKENS.REVEAL_OFFSET_Y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "0px" }}
      animate={{ y: [0, -2, 0] }}
      transition={{
        opacity: { duration: MOTION_TOKENS.DURATION_REVEAL, ease: MOTION_TOKENS.EASING_REVEAL, delay: index * MOTION_TOKENS.STAGGER_SMALL },
        filter: { duration: MOTION_TOKENS.DURATION_REVEAL, ease: MOTION_TOKENS.EASING_REVEAL, delay: index * MOTION_TOKENS.STAGGER_SMALL },
        y: {
          repeat: Infinity,
          duration: MOTION_TOKENS.IDLE_BREATHING_FLOATING + (index % 3),
          ease: MOTION_TOKENS.EASING_IDLE,
          delay: phaseDelay,
        },
      }}
      style={{
        transform: `translateZ(${activeZ}px) ${isHovered ? 'translateY(-6px)' : ''}`,
        transformStyle: "preserve-3d",
      }}
      className={`
        group relative block w-full rounded-2xl overflow-hidden
        bg-[#121316]/90 backdrop-blur-xl border border-white/10
        transition-all duration-500 cubic-bezier(0.25, 1, 0.5, 1)
        ${isHovered 
          ? "shadow-[0_40px_80px_rgba(0,0,0,0.85),inset_0_1px_0_rgba(255,255,255,0.25)] border-white/20" 
          : "shadow-[0_20px_50px_rgba(0,0,0,0.6),inset_0_1px_0_rgba(255,255,255,0.1)]"}
        ${isPrimary ? "md:col-span-2 min-h-[460px] sm:min-h-[500px]" : "min-h-[420px]"}
      `}
    >
      <ArticleLink article={article} section="LatestNews" position={index} className="flex flex-col h-full w-full" style={{ transformStyle: "preserve-3d" }}>
        
        {/* Soft Glare Specular Highlight */}
        <div 
          className={`
            absolute inset-0 pointer-events-none z-40 transition-opacity duration-700 overflow-hidden
            ${isHovered ? "opacity-100" : "opacity-0"}
          `}
          style={{ transform: "translateZ(2px)" }}
        >
          <div className="absolute -top-[50%] -bottom-[50%] -left-[100%] w-[200%] bg-[linear-gradient(115deg,transparent_42%,rgba(255,255,255,0.06)_48%,rgba(255,255,255,0.25)_50%,rgba(255,255,255,0.06)_52%,transparent_58%)] group-hover:translate-x-[60%] transition-transform duration-1000 ease-out" />
        </div>

        {/* Editorial Window (Image Showcase: 50-55% of card height, elevated slightly above glass) */}
        <div 
          className={`relative w-full overflow-hidden bg-muted/40 ${isPrimary ? "h-[240px] sm:h-[280px]" : "h-[210px] sm:h-[230px]"}`}
          style={{ transform: "translateZ(18px)", transformStyle: "preserve-3d" }}
        >
          <ArticleThumbnail
            article={article}
            className="w-full h-full rounded-t-2xl overflow-hidden"
            imgClassName="object-cover"
            sizes="(max-width: 768px) 100vw, 50vw"
          />
          {/* Subtle Vignette Overlay over Image bottom */}
          <div className="absolute inset-0 bg-gradient-to-t from-[#121316] via-transparent to-transparent opacity-90" />
        </div>

        {/* Panel Editorial Content Body */}
        <div className="p-6 sm:p-8 flex flex-col flex-1 justify-between relative z-20">
          <div>
            {/* Source Tag & Document Badge */}
            <div className="mb-3">
              <CardHeader badge={presentation.badge} category={article.category || article.source} />
            </div>

            {/* Inline Topics for Collection / Newsletter Cards */}
            {presentation.cardVariant === "collection" && (article.primary_topics || article.primaryTopics) && (
              <div className="mb-3">
                <CardTopics topics={article.primary_topics || article.primaryTopics} maxDisplay={3} />
              </div>
            )}

            {/* Headline (Visual Focus - Typography static on hover) */}
            <h3 className={`font-serif font-bold text-foreground leading-[1.25] tracking-tight mb-3 ${isPrimary ? "text-2xl sm:text-3xl lg:text-4xl" : "text-xl sm:text-2xl"}`}>
              {article.title}
            </h3>

            {/* Summary */}
            <p className="text-muted-foreground text-xs sm:text-sm line-clamp-2 leading-relaxed mb-6">
              {article.summary}
            </p>
          </div>

          {/* Metadata & CTA Row */}
          <div className="pt-4 border-t border-white/5 flex items-center justify-between mt-auto">
            <div className="flex items-center gap-3 text-[11px] font-mono text-muted-foreground uppercase tracking-wider">
              <span className="flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-primary/70" />
                <span suppressHydrationWarning>{article.published_at ? new Date(article.published_at).toLocaleDateString('en-US', { timeZone: 'UTC' }) : 'TODAY'}</span>
              </span>
              <span>•</span>
              <span>{Math.max(2, Math.round((article.title?.length || 50) / 20))}M READ</span>
            </div>

            <div className={`flex items-center gap-1.5 text-xs font-mono tracking-widest uppercase transition-colors duration-300 ${isHovered ? "text-primary" : "text-muted-foreground/70"}`}>
              <span>Read Article</span>
              <ArrowRight className={`w-3.5 h-3.5 transition-transform duration-300 ${isHovered ? "translate-x-1" : ""}`} />
            </div>
          </div>

        </div>
      </ArticleLink>
    </m.div>
  );
}
