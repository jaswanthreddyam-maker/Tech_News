"use client";

import React from "react";
import { ShimmerBase } from "@/components/skeletons/ShimmerBase";

/**
 * HeroCarouselSkeleton — 1:1 Pixel-Perfect Mirror for HeroScene (Pitch OLED Black Editorial Stage)
 * Guarantees zero Cumulative Layout Shift (CLS = 0) and seamless transition into the 3D ring.
 */
export function HeroCarouselSkeleton() {
  return (
    <div className="relative w-full min-h-[480px] sm:min-h-[520px] md:min-h-[640px] xl:min-h-[680px] pt-1 px-4 sm:px-6 lg:px-8 pb-12 sm:pb-16 md:pb-12 lg:pb-4 flex items-center justify-center">
      <div className="relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-2 sm:gap-4 lg:gap-8 xl:gap-12 items-center w-full max-w-[1400px] mx-auto">
        
        {/* Left Editorial Panel Skeleton (lg:col-span-5) — Exact 1:1 match with HeroEditorialPanel */}
        <div className="lg:col-span-5 flex flex-col justify-start max-w-[540px] w-full mx-auto lg:mx-0 z-20 order-1 lg:order-1 -translate-y-2 sm:-translate-y-4 lg:-translate-y-[40px] pt-1 sm:pt-2 lg:pt-0 flex flex-col gap-3.5 sm:gap-5">
          {/* Badge, Category & Read Time Row */}
          <div className="flex items-center gap-3">
            <ShimmerBase className="h-6 w-28 rounded-md" />
            <span className="text-white/20 text-xs font-mono">•</span>
            <ShimmerBase className="h-4 w-16 rounded" />
            <span className="text-white/20 text-xs font-mono">•</span>
            <ShimmerBase className="h-4 w-20 rounded" />
          </div>

          {/* Headline (2 lines of architectural bold typography matching H1) */}
          <div className="space-y-3 w-[90%] max-w-[360px] md:w-full md:max-w-none">
            <ShimmerBase className="h-8 sm:h-9 lg:h-10 xl:h-11 w-full rounded-lg" />
            <ShimmerBase className="h-8 sm:h-9 lg:h-10 xl:h-11 w-[82%] rounded-lg" />
          </div>

          {/* Read Story CTA Link with Signature Underline */}
          <div className="pt-2 flex flex-col gap-1 w-28">
            <ShimmerBase className="h-5 w-24 rounded" />
            <div className="h-0.5 w-12 rounded-full bg-primary/30" />
          </div>
        </div>

        {/* Right 3D Ring Stage Skeleton (lg:col-span-7) — Exact 1:1 match with HeroScene line 62 */}
        <div className="lg:col-span-7 relative w-full flex flex-col items-center justify-center z-10 order-2 lg:order-2 h-[310px] sm:h-[370px] md:h-[440px] lg:h-[480px] -mt-8 sm:-mt-8 lg:mt-0 -translate-y-[80px] sm:-translate-y-[60px] md:-translate-y-[40px] lg:-translate-y-[30px]">
          <div className="relative w-full h-full flex items-center justify-center">
            {/* Left Flanking Perspective Card Skeleton */}
            <div className="hidden sm:block absolute left-4 lg:left-10 w-[190px] sm:w-[220px] lg:w-[260px] aspect-[4/5] rounded-2xl bg-neutral-900/60 border border-white/10 opacity-30 transform -rotate-12 scale-90 pointer-events-none" />

            {/* Active Center 3D Extruded Slab Card Skeleton (1:1 match with HeroMediaCard) */}
            <div className="relative z-20 w-[220px] sm:w-[260px] lg:w-[304px] aspect-[4/5] rounded-2xl bg-black border border-white/20 overflow-hidden shadow-[0_25px_50px_-10px_rgba(0,0,0,0.95)]">
              {/* Foreground Image Layer (Top 55% Full Width Edge-to-Edge) */}
              <div className="absolute top-0 inset-x-0 w-full h-[55%] overflow-hidden bg-neutral-900">
                <ShimmerBase className="w-full h-full" />
                {/* Category Pill on Top Left */}
                <div className="absolute top-3.5 left-3.5 z-20">
                  <ShimmerBase className="h-5 w-16 rounded-md" />
                </div>
              </div>

              {/* Bottom 45% Content Area */}
              <div className="absolute bottom-0 inset-x-0 w-full h-[45%] p-4 sm:p-5 flex flex-col justify-end gap-2 bg-gradient-to-t from-black via-black/95 to-transparent z-20">
                <ShimmerBase className="h-4 w-5/6 rounded" />
                <ShimmerBase className="h-4 w-3/5 rounded" />
                <div className="flex items-center justify-between pt-2 mt-1 border-t border-white/10">
                  <ShimmerBase className="h-3 w-16 rounded" />
                  <ShimmerBase className="h-3 w-12 rounded" />
                </div>
              </div>
            </div>

            {/* Right Flanking Perspective Card Skeleton */}
            <div className="hidden sm:block absolute right-4 lg:right-10 w-[190px] sm:w-[220px] lg:w-[260px] aspect-[4/5] rounded-2xl bg-neutral-900/60 border border-white/10 opacity-30 transform rotate-12 scale-90 pointer-events-none" />
          </div>
        </div>

      </div>
    </div>
  );
}
