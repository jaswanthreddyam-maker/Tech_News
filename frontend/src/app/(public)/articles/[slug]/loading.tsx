"use client";

import React from "react";
import { Container } from "@/components/layout/Container";
import { ShimmerBase } from "@/components/skeletons/ShimmerBase";
import { AdaptiveCardSkeleton } from "@/components/skeletons/AdaptiveCardSkeleton";

/**
 * ArticleLoading — 1:1 Mirror for ArticleLayout (max-w-5xl Expanded View)
 * Zero Cumulative Layout Shift (CLS) on desktop, tablet, and mobile.
 */
export default function ArticleLoading() {
  return (
    <Container size="wide" className="mt-8 mb-20">
      <div className="flex flex-col xl:flex-row gap-8 lg:gap-12 relative xl:ml-12">
        {/* Floating Actions Skeleton (Desktop left rail) */}
        <div className="hidden xl:flex flex-col items-center gap-3 sticky top-32 h-fit w-16 shrink-0 p-3 rounded-full bg-background/80 border border-border/40 backdrop-blur">
          {[1, 2, 3, 4].map((i) => (
            <ShimmerBase key={i} className="w-10 h-10 rounded-full" />
          ))}
        </div>

        {/* Main Content Column (expands to fill max-w-5xl) */}
        <div className="flex-1 min-w-0 max-w-5xl mx-auto xl:mx-0 w-full space-y-8">
          {/* Header Skeleton */}
          <div className="space-y-6">
            {/* Meta tags: Badge + Calendar + Read Time */}
            <div className="flex items-center gap-3">
              <ShimmerBase className="h-6 w-24 rounded-full" />
              <ShimmerBase className="h-4 w-32 rounded" />
              <ShimmerBase className="h-4 w-20 rounded" />
            </div>

            {/* Title (Large font-serif headline matching 3xl/5xl scale) */}
            <div className="space-y-3">
              <ShimmerBase className="h-10 sm:h-12 w-full rounded-lg" />
              <ShimmerBase className="h-10 sm:h-12 w-[78%] rounded-lg" />
            </div>

            {/* Lead Story Description (max-w-4xl) */}
            <div className="space-y-2 pt-1 max-w-4xl">
              <ShimmerBase className="h-4 sm:h-5 w-full rounded" />
              <ShimmerBase className="h-4 sm:h-5 w-4/5 rounded" />
            </div>

            {/* Reading Mode Preferences Control Bar */}
            <div className="flex items-center justify-between border-t border-b border-border/50 py-3">
              <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
                <ShimmerBase className="h-6 w-20 rounded-full" />
                <ShimmerBase className="h-6 w-20 rounded-full" />
                <ShimmerBase className="h-6 w-24 rounded-full" />
              </div>
              <ShimmerBase className="h-6 w-24 rounded-md" />
            </div>
          </div>

          {/* Hero Image Skeleton */}
          <div className="w-full">
            <ShimmerBase className="w-full h-[320px] sm:h-[400px] md:h-[450px] rounded-xl" />
          </div>

          {/* AI Executive Summary Card Skeleton */}
          <div className="w-full rounded-2xl border border-white/10 bg-card/40 p-6 sm:p-8 space-y-4 shadow-sm">
            <div className="flex items-center gap-2 pb-2">
              <ShimmerBase className="w-5 h-5 rounded-full" />
              <ShimmerBase className="h-4 w-36 rounded" />
            </div>
            <div className="space-y-2.5">
              <ShimmerBase className="h-4 w-full rounded" />
              <ShimmerBase className="h-4 w-full rounded" />
              <ShimmerBase className="h-4 w-[92%] rounded" />
              <ShimmerBase className="h-4 w-[70%] rounded" />
            </div>
          </div>

          {/* Article Prose Body Skeleton */}
          <article className="space-y-6 pt-4">
            <div className="space-y-3">
              <ShimmerBase className="h-4 sm:h-5 w-full rounded" />
              <ShimmerBase className="h-4 sm:h-5 w-full rounded" />
              <ShimmerBase className="h-4 sm:h-5 w-[94%] rounded" />
              <ShimmerBase className="h-4 sm:h-5 w-[86%] rounded" />
            </div>

            {/* Heading 2 in text */}
            <div className="pt-6 pb-2">
              <ShimmerBase className="h-8 w-64 rounded-md" />
            </div>

            <div className="space-y-3">
              <ShimmerBase className="h-4 sm:h-5 w-full rounded" />
              <ShimmerBase className="h-4 sm:h-5 w-full rounded" />
              <ShimmerBase className="h-4 sm:h-5 w-[90%] rounded" />
            </div>

            {/* Blockquote Skeleton */}
            <div className="border-l-4 border-primary/40 pl-5 py-2 space-y-2 my-6">
              <ShimmerBase className="h-4 w-full rounded italic" />
              <ShimmerBase className="h-4 w-3/4 rounded italic" />
              <ShimmerBase className="h-3 w-32 rounded pt-1" />
            </div>

            <div className="space-y-3">
              <ShimmerBase className="h-4 sm:h-5 w-full rounded" />
              <ShimmerBase className="h-4 sm:h-5 w-4/5 rounded" />
            </div>
          </article>

          {/* Key Takeaways Card Skeleton */}
          <div className="w-full rounded-2xl border border-white/10 bg-card/30 p-6 sm:p-8 space-y-4">
            <div className="flex items-center gap-2 pb-2">
              <ShimmerBase className="w-4 h-4 rounded" />
              <ShimmerBase className="h-5 w-36 rounded" />
            </div>
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-start gap-3">
                  <ShimmerBase className="w-2 h-2 rounded-full mt-2 shrink-0" />
                  <ShimmerBase className="h-4 w-full rounded" />
                </div>
              ))}
            </div>
          </div>

          {/* Primary Source Dispatch Link Skeleton */}
          <div className="p-5 rounded-2xl bg-white/[0.03] border border-white/10 space-y-3 mt-6">
            <ShimmerBase className="h-4 w-40 rounded" />
            <ShimmerBase className="h-3.5 w-full rounded" />
            <ShimmerBase className="h-8 w-44 rounded-xl mt-2" />
          </div>

          {/* Related Stories Grid Skeleton */}
          <div className="pt-10 border-t border-border/40 space-y-6">
            <div className="space-y-2">
              <ShimmerBase className="h-3 w-20 rounded" />
              <ShimmerBase className="h-7 w-48 rounded-md" />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <AdaptiveCardSkeleton />
              <AdaptiveCardSkeleton />
            </div>
          </div>

        </div>
      </div>
    </Container>
  );
}
