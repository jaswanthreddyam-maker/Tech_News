"use client";

import React from "react";
import Image from "next/image";
import { FeaturedArticle } from "../types";
import { useHeroScene } from "./HeroSceneProvider";
import { ArticleLink } from "@/domains/article/ArticleLink";

interface HeroMediaCardProps {
  article: FeaturedArticle;
  index: number;
  isActive: boolean;
  arrivalFinished?: boolean;
  style?: React.CSSProperties;
  className?: string;
}

/**
 * HeroMediaCard — True 3D Extruded Slab Card
 */
export function HeroMediaCard({ article, index, isActive, arrivalFinished: propArrivalFinished, style, className = "" }: HeroMediaCardProps) {
  const { arrivalFinished: contextArrivalFinished, setActiveIndex, setInteractionMode, setFocusedCardId, onPrimaryAction } = useHeroScene();
  const arrivalFinished = propArrivalFinished ?? contextArrivalFinished;
  const getHeroImg = (art: FeaturedArticle) => {
    if ((art as any).thumbnail_url) return (art as any).thumbnail_url;
    if (art.thumbnail && art.thumbnail.startsWith("http")) return art.thumbnail;
    if ((art as any).image_url) return (art as any).image_url;
    if (art.thumbnail) return art.thumbnail;
    if ((art as any).thumbnail_local) {
      const l = (art as any).thumbnail_local;
      if (l.startsWith('/app/uploads/')) return l.replace('/app/uploads/', '/api/v1/uploads/');
      return l;
    }
    return "";
  };

  const [imgSrc, setImgSrc] = React.useState(getHeroImg(article));

  React.useEffect(() => {
    setImgSrc(getHeroImg(article));
  }, [article]);

  const handleClick = (e: React.MouseEvent) => {
    if (!isActive) {
      e.preventDefault();
      e.stopPropagation();
      setActiveIndex(index);
    } else if (onPrimaryAction) {
      onPrimaryAction(article);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      if (!isActive) {
        e.preventDefault();
        e.stopPropagation();
        setActiveIndex(index);
      } else if (onPrimaryAction) {
        onPrimaryAction(article);
      }
    }
  };

  return (
    <ArticleLink
      article={article}
      section="Hero3DRing"
      position={index}
      prefetchPriority={isActive}
      onClick={handleClick}
      onPointerDown={() => {
        if (isActive) {
          setInteractionMode("hover");
          setFocusedCardId(article.id);
        }
      }}
      style={{
        ...style,
        transformStyle: "preserve-3d",
      }}
      className={`group absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[247px] sm:w-[285px] md:w-[304px] aspect-[4/5] cursor-pointer transition-[transform,opacity,border-color,box-shadow] duration-500 select-none outline-none focus-visible:ring-2 focus-visible:ring-primary ${className}`}
    >
      {/* 3D Physical Extruded Slab Back Plate (Gives True 3D Depth) */}
      <div 
        className="absolute inset-0 rounded-2xl bg-neutral-950 border border-white/20 shadow-[0_30px_60px_rgba(0,0,0,0.95)] pointer-events-none"
        style={{
          transform: "translateZ(-14px)",
        }}
      />

      {/* 3D Slab Thickness Ring Frame */}
      <div 
        className="absolute inset-0 rounded-2xl border border-white/10 bg-white/[0.03] pointer-events-none"
        style={{
          transform: "translateZ(-7px)",
        }}
      />

      {/* Front Face Glass Card Container */}
      <div
        className={`relative w-full h-full flex flex-col bg-black rounded-2xl overflow-hidden border transition-all duration-500 cubic-bezier(0.4, 0, 0.2, 1) ${
          isActive
            ? "border-white/45 ring-1 ring-white/30 shadow-[0_25px_50px_-10px_rgba(0,0,0,0.95),0_0_30px_rgba(255,255,255,0.15),inset_0_1px_1px_rgba(255,255,255,0.5)] hover:border-white/70 hover:shadow-[0_30px_60px_-10px_rgba(0,0,0,0.95),0_0_40px_rgba(255,255,255,0.25)] hover:-translate-y-[4px]"
            : "border-white/20 shadow-[inset_0_1px_1px_rgba(255,255,255,0.3),0_15px_30px_rgba(0,0,0,0.8)] opacity-85 grayscale-[10%] hover:opacity-100 hover:grayscale-0 hover:border-white/45 hover:shadow-[0_0_28px_rgba(255,255,255,0.2)]"
        }`}
        style={{
          transformStyle: "preserve-3d",
        }}
      >
        {article.id.startsWith("skeleton-") ? (
          <div className="absolute inset-0 w-full h-full bg-neutral-950 overflow-hidden">
            <div className="absolute top-0 inset-x-0 w-full h-[55%] z-10 overflow-hidden bg-neutral-900 animate-pulse" />
            <div className="absolute bottom-0 w-full p-4 sm:p-5 lg:p-6 flex flex-col justify-end z-30">
              <div className="h-5 w-5/6 bg-neutral-800 rounded animate-pulse mb-2"></div>
              <div className="h-5 w-2/3 bg-neutral-800 rounded animate-pulse"></div>
            </div>
          </div>
        ) : (
          <>
            {/* Layer 1: Full Bleed Media Showcase (Full Width Image + Blurred Ambient Fill) */}
            <div className="absolute inset-0 w-full h-full overflow-hidden bg-neutral-950">
              {imgSrc ? (
                <>
                  {/* Blurred Background Layer (Fills entire card) */}
                  <div className="absolute inset-0 w-full h-full overflow-hidden">
                    <Image
                      src={imgSrc}
                      alt=""
                      fill
                      unoptimized={true}
                      quality={50}
                      priority={false}
                      aria-hidden="true"
                      className="object-cover scale-125 blur-2xl opacity-75 transition-transform duration-700 group-hover:scale-135 group-hover:saturate-[1.08]"
                    />
                    {/* Dark Gradient Overlay for Contrast */}
                    <div className="absolute inset-0 bg-gradient-to-b from-black/20 via-black/40 to-black/95" />
                  </div>

                  {/* Foreground Image Layer (Top 55% Area, Full Width Edge-to-Edge) */}
                  <div className="absolute top-0 inset-x-0 w-full h-[55%] z-10 overflow-hidden">
                    <Image
                      src={imgSrc}
                      alt={article.title}
                      fill
                      unoptimized={true}
                      sizes="(max-width: 768px) 290px, 340px"
                      quality={90}
                      priority={isActive || index === 0}
                      onError={() => setImgSrc("")}
                      className="object-cover object-center w-full h-full drop-shadow-[0_8px_16px_rgba(0,0,0,0.6)] transition-all duration-700 group-hover:scale-[1.04]"
                    />
                    {/* Shaded Division Seam Gradient at Bottom of Thumbnail */}
                    <div className="absolute inset-x-0 bottom-0 h-10 bg-gradient-to-b from-transparent via-black/40 to-black/95 pointer-events-none z-15" />
                  </div>
                </>
              ) : (
                <div className="w-full h-full flex flex-col justify-end p-6 bg-gradient-to-br from-neutral-900 via-neutral-950 to-black relative">
                  <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-blue-900/20 via-purple-900/10 to-transparent" />
                </div>
              )}

              {/* Category Pill Overlaid on Top Left */}
              <div className="absolute top-3.5 left-3.5 z-20">
                <span className="px-2.5 py-1 text-[9px] font-mono uppercase tracking-[0.18em] font-bold rounded-full bg-black/60 backdrop-blur-xl border border-white/25 text-white shadow-[0_2px_8px_rgba(0,0,0,0.5),inset_0_1px_1px_rgba(255,255,255,0.4)] group-hover:border-white/50 group-hover:shadow-[0_0_12px_rgba(255,255,255,0.3)] transition-all duration-300">
                  {article.category || "TECH"}
                </span>
              </div>
            </div>

            {/* Layer 2: Photorealistic Specular Sheen */}
            <div 
              className="absolute inset-0 pointer-events-none z-20 mix-blend-overlay transition-opacity duration-500 opacity-40 group-hover:opacity-85"
              style={{
                background: 'linear-gradient(135deg, rgba(255,255,255,0.4) 0%, rgba(255,255,255,0.12) 25%, transparent 55%, rgba(0,0,0,0.3) 100%)',
              }}
            />

            {/* Layer 3: Photorealistic Optical Glare Sweep */}
            <div className="absolute inset-0 pointer-events-none z-25 overflow-hidden">
              <div 
                className="absolute -top-[50%] -bottom-[50%] -left-[160%] w-[320%] bg-[linear-gradient(115deg,transparent_40%,rgba(255,255,255,0.03)_47%,rgba(255,255,255,0.25)_50%,rgba(255,255,255,0.03)_53%,transparent_60%)] group-hover:translate-x-[70%] transition-transform duration-[1100ms] cubic-bezier(0.16,1,0.3,1)"
                style={{ willChange: "transform" }}
              />
            </div>

            {/* Layer 4: Fresnel Top-Edge Specular Catch */}
            <div className="absolute inset-0 pointer-events-none z-30 rounded-2xl border border-white/15 shadow-[inset_0_1px_1px_rgba(255,255,255,0.45),inset_0_-1px_1px_rgba(0,0,0,0.6)] group-hover:border-white/40 transition-colors duration-500" />

            {/* Layer 5: Exact 45% Height Description Overlay Footer (Trending Now Glass Material) */}
            <div className={`absolute bottom-0 inset-x-0 h-[45%] pt-5 pb-5 px-6 bg-neutral-950/80 backdrop-blur-xl border-t border-white/15 shadow-[0_-12px_32px_rgba(0,0,0,0.65),inset_0_1px_0_rgba(255,255,255,0.2)] flex flex-col items-center justify-center text-center gap-1.5 z-35 transition-all duration-700 ease-out ${
              arrivalFinished ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4 pointer-events-none"
            }`}>
              <span className="text-[11.5px] font-mono tracking-[0.2em] uppercase text-white/80 font-bold truncate">
                {article.source || "OPENAI BLOG"}
              </span>
              <h4 className="text-[15.5px] font-semibold leading-[1.35] tracking-tight text-white/95 line-clamp-3">
                {article.title}
              </h4>
            </div>
          </>
        )}
      </div>
    </ArticleLink>
  );
}
