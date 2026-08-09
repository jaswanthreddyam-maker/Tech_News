"use client";

import { Clock } from "lucide-react";
import { StoryCardProps } from "./types";
import { getCategory, formatReadTime, getSource, getImageUrl } from "./helpers";
import { ArticleImage } from "./ArticleImage";
import { useCardTilt } from "./useCardTilt";
import { ArticleLink } from "@/domains/article/ArticleLink";
import { PhysicalCard3D } from "./PhysicalCard3D";
import { PhysicalLighting } from "./PhysicalLighting";
import { PHYSICAL_DEPTH } from "./constants";

/**
 * FeaturedStory — 3D Physical Extruded Hero Slab Content Provider
 * Layer Hierarchy: MotionReveal -> PhysicalCard3D (Geometry) -> LightingLayer -> FrontFace -> TiltLayer -> ArticleLink -> Editorial Content
 */
export function FeaturedStory({ article, onClick }: StoryCardProps) {
  const cardRef = useCardTilt<HTMLDivElement>({
    maxTiltDeg: 7,
    maxTranslateZ: 12,
    scaleOnHover: 1.015,
  });

  const category = getCategory(article);
  const readTime = formatReadTime(article, false);
  const source = getSource(article);
  const imageUrl = getImageUrl(article);

  return (
    <PhysicalCard3D
      thickness={14}
      roundedClass="rounded-[18px]"
      frontFaceClassName="p-6 bg-neutral-950/85 hover:bg-neutral-900/95 border border-white/15 border-t-white/60 border-r-white/30 group-hover:border-t-white/90 group-hover:border-r-white/50 shadow-[0_20px_50px_rgba(0,0,0,0.6),inset_0_1px_0_rgba(255,255,255,0.25)] hover:shadow-[0_36px_72px_rgba(0,0,0,0.9),inset_0_1px_0_rgba(255,255,255,0.45)] drop-shadow-[0_16px_32px_rgba(0,0,0,0.5)]"
      lighting={
        <PhysicalLighting
          roundedClass="rounded-[18px]"
          specularClassName="right-6 w-24 group-hover:w-36"
        />
      }
    >
      {/* Hover Lift Layer (Reserved for future hover elevation, click-bounce, etc.) */}
      <div className="w-full h-full" style={{ transformStyle: "preserve-3d" }}>
        {/* Tilt Layer (Owns cursor tracking transform independently) */}
        <div
          ref={cardRef}
          className="w-full h-full"
          style={{
            transformStyle: "preserve-3d",
            transform: "rotateX(var(--tilt-x, 0deg)) rotateY(var(--tilt-y, 0deg)) translateZ(var(--tilt-z, 0px)) scale3d(var(--tilt-scale, 1), var(--tilt-scale, 1), 1)",
          }}
        >
        {/* Navigation Layer */}
        <ArticleLink
          article={article}
          section="TrendingStories"
          position={0}
          prefetchPriority={true}
          onClick={onClick}
          className="flex flex-col w-full h-full no-underline"
        >
          {/* Extruded Hero Image */}
          <div
            className="relative z-10 w-full mb-5 rounded-[12px] overflow-hidden shadow-[0_12px_28px_rgba(0,0,0,0.6)] group-hover:shadow-[0_20px_40px_rgba(0,0,0,0.85)] transition-all duration-300"
            style={{ transform: `translateZ(${PHYSICAL_DEPTH.hero.image}px)` }}
          >
            <ArticleImage
              src={imageUrl}
              alt={article.title || "Featured Story"}
              category={category}
              aspectRatio="aspect-[4/3]"
              className="w-full rounded-[12px] ring-1 ring-white/20 origin-center transition-all duration-300 group-hover:contrast-[1.04] group-hover:saturate-[1.05]"
            />
          </div>

          {/* Extruded Editorial Content Column */}
          <div className="relative z-10 flex flex-col flex-1" style={{ transformStyle: "preserve-3d" }}>
            {/* Category Badge */}
            <div
              className="inline-block self-start px-2.5 py-0.5 rounded-md bg-primary/15 text-primary text-xs font-mono font-semibold uppercase tracking-wider mb-3 border border-primary/20 shadow-sm"
              style={{ transform: `translateZ(${PHYSICAL_DEPTH.hero.badge}px)` }}
            >
              {category}
            </div>

            {/* Title */}
            <h3
              className="text-2xl font-bold tracking-tight text-foreground leading-snug line-clamp-2 mb-3 group-hover:text-primary transition-colors duration-200"
              style={{ transform: `translateZ(${PHYSICAL_DEPTH.hero.title}px)` }}
            >
              {article.title}
            </h3>

            {/* Lede Summary */}
            <p
              className="text-sm text-muted-foreground/90 line-clamp-2 mb-5 pl-3 border-l-2 border-primary/40"
              style={{ transform: `translateZ(${PHYSICAL_DEPTH.hero.summary}px)` }}
            >
              {article.summary ||
                article.description ||
                "Read the latest deep-dive analysis on this emerging technical breakthrough."}
            </p>

            {/* Metadata Rail */}
            <div
              className="flex items-center justify-between text-xs font-mono text-foreground/75 group-hover:text-foreground/95 pt-4 border-t border-border/25 mt-auto transition-colors duration-200"
              style={{ transform: `translateZ(${PHYSICAL_DEPTH.hero.metadata}px)` }}
            >
              <span className="truncate max-w-[160px] font-medium">{source}</span>
              <div className="flex items-center gap-1.5 text-muted-foreground/85 group-hover:text-foreground/90">
                <Clock className="w-3.5 h-3.5" />
                <span>{readTime}</span>
              </div>
            </div>
          </div>
        </ArticleLink>
        </div>
      </div>
    </PhysicalCard3D>
  );
}
