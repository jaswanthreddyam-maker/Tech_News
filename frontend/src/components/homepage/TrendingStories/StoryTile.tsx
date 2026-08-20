"use client";

import { StoryCardProps } from "./types";
import { getCategory, formatReadTime, getSource, getImageUrl } from "./helpers";
import { ArticleImage } from "./ArticleImage";
import { useCardTilt } from "./useCardTilt";
import { ArticleLink } from "@/domains/article/ArticleLink";
import { PhysicalCard3D } from "./PhysicalCard3D";
import { PhysicalLighting } from "./PhysicalLighting";
import { PHYSICAL_DEPTH, TRENDING_LAYOUT } from "./constants";

/**
 * StoryTile — 3D Physical Extruded Tile Slab Content Provider
 * Layer Hierarchy: MotionReveal -> PhysicalCard3D (Geometry) -> LightingLayer -> FrontFace -> TiltLayer -> ArticleLink -> Editorial Content
 */
export function StoryTile({ article, onClick }: StoryCardProps) {
  const cardRef = useCardTilt<HTMLDivElement>({
    maxTiltDeg: 6,
    maxTranslateZ: 10,
    scaleOnHover: 1.015,
  });

  const category = getCategory(article);
  const readTime = formatReadTime(article, true);
  const source = getSource(article);
  const imageUrl = getImageUrl(article);

  return (
    <PhysicalCard3D
      thickness={12}
      roundedClass="rounded-[16px]"
      frontFaceClassName="p-5 bg-neutral-950/80 hover:bg-neutral-900/90 border border-white/15 border-t-white/50 border-r-white/25 group-hover:border-t-white/80 group-hover:border-r-white/40 shadow-[0_12px_30px_rgba(0,0,0,0.4),inset_0_1px_0_rgba(255,255,255,0.2)] hover:shadow-[0_28px_56px_rgba(0,0,0,0.85),inset_0_1px_0_rgba(255,255,255,0.35)] drop-shadow-[0_10px_20px_rgba(0,0,0,0.4)]"
      lighting={
        <PhysicalLighting
          roundedClass="rounded-[16px]"
          specularClassName="right-4 w-16 group-hover:w-24"
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
          onClick={onClick}
          className="flex flex-row items-stretch justify-between gap-4 w-full h-full no-underline"
        >
          {/* Extruded Content Column */}
          <div
            className="relative z-10 flex flex-col flex-1 min-w-0"
            style={{ transformStyle: "preserve-3d" }}
          >
            <div>
              {/* Category Badge */}
              <div
                className="text-xs font-mono font-medium text-primary uppercase tracking-wider mb-2"
                style={{ transform: `translateZ(${PHYSICAL_DEPTH.tile.badge}px)` }}
              >
                {category}
              </div>

              {/* Title */}
              <h4
                className="text-base font-semibold leading-snug text-foreground line-clamp-2 mb-3 group-hover:text-primary transition-colors duration-200"
                style={{ transform: `translateZ(${PHYSICAL_DEPTH.tile.title}px)` }}
              >
                {article.title}
              </h4>
            </div>

            {/* Metadata Rail */}
            <div
              className="flex items-center gap-2.5 text-xs font-mono text-foreground/70 group-hover:text-foreground/90 mt-auto pt-1 transition-colors duration-200"
              style={{ transform: `translateZ(${PHYSICAL_DEPTH.tile.metadata}px)` }}
            >
              <span className="truncate max-w-[120px] font-medium">{source}</span>
              <span className="text-muted-foreground/40">•</span>
              <span className="text-muted-foreground/85">{readTime}</span>
            </div>
          </div>

          {/* Extruded Inset Thumbnail using TRENDING_LAYOUT.THUMBNAIL_SIZE */}
          <div
            className="relative z-10 rounded-[10px] overflow-hidden flex-none bg-black/50 ring-1 ring-white/20 p-0.5 self-center origin-center shadow-[0_8px_20px_rgba(0,0,0,0.6)] group-hover:shadow-[0_14px_28px_rgba(0,0,0,0.8)] transition-all duration-300"
            style={{
              width: TRENDING_LAYOUT.THUMBNAIL_SIZE,
              height: TRENDING_LAYOUT.THUMBNAIL_SIZE,
              transform: `translateZ(${PHYSICAL_DEPTH.tile.thumbnail}px)`,
            }}
          >
            <ArticleImage
              src={imageUrl}
              alt={article.title || "Story Thumbnail"}
              category={category}
              seed={article.id || article.slug || article.title}
              aspectRatio="aspect-square"
              className="w-full h-full rounded-[8px] group-hover:contrast-[1.04] group-hover:saturate-[1.05]"
            />
          </div>
        </ArticleLink>
        </div>
      </div>
    </PhysicalCard3D>
  );
}
