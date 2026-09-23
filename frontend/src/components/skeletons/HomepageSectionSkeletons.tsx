"use client";

import React from "react";
import { ShimmerBase } from "./ShimmerBase";
import { EditorialCardSkeleton } from "./EditorialCardSkeleton";

/**
 * CategoryNewsSkeleton — 1:1 Mirror for LatestNews (Explore by Category)
 */
export const CategoryNewsSkeleton = React.memo(function CategoryNewsSkeleton() {
  return (
    <section className="py-12 border-t border-border/20 mt-8 min-h-[400px] relative rounded-3xl overflow-hidden bg-gradient-to-b from-[#0e0f12]/40 via-background to-background p-4 sm:p-8 lg:p-10">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <ShimmerBase className="w-10 h-10 rounded-xl" />
        <div className="space-y-1.5">
          <ShimmerBase className="h-7 w-56 rounded-md" />
          <ShimmerBase className="h-3.5 w-72 rounded" />
        </div>
      </div>

      {/* Category Pills Row */}
      <div className="flex items-center gap-2 overflow-x-auto pb-4 mb-8 no-scrollbar">
        {["All", "AI & ML", "Cybersecurity", "Cloud & Infra", "Hardware", "Startups"].map((_, i) => (
          <ShimmerBase key={i} className="h-8 w-24 rounded-full flex-shrink-0" />
        ))}
      </div>

      {/* 4-Card Responsive Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 w-full">
        <EditorialCardSkeleton />
        <EditorialCardSkeleton />
        <EditorialCardSkeleton />
        <EditorialCardSkeleton />
      </div>
    </section>
  );
});

/**
 * StoryEvolutionSkeleton — 1:1 Mirror for StoryEvolution Timeline
 */
export const StoryEvolutionSkeleton = React.memo(function StoryEvolutionSkeleton() {
  return (
    <div className="w-full py-8 my-4 rounded-2xl border border-border/30 bg-card/20 p-6 sm:p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-1.5">
          <ShimmerBase className="h-6 w-44 rounded-md" />
          <ShimmerBase className="h-3 w-64 rounded" />
        </div>
        <ShimmerBase className="h-6 w-20 rounded-full" />
      </div>

      {/* Timeline Nodes Track */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="p-4 rounded-xl border border-border/30 bg-background/40 space-y-3">
            <div className="flex items-center justify-between">
              <ShimmerBase className="h-3 w-16 rounded" />
              <ShimmerBase className="h-2.5 w-12 rounded-full" />
            </div>
            <ShimmerBase className="h-4 w-full rounded" />
            <ShimmerBase className="h-4 w-3/4 rounded" />
            <ShimmerBase className="h-3 w-20 rounded mt-2" />
          </div>
        ))}
      </div>
    </div>
  );
});

/**
 * BreakingNewsSkeleton — 1:1 Mirror for BreakingNews Ticker
 */
export const BreakingNewsSkeleton = React.memo(function BreakingNewsSkeleton() {
  return (
    <div className="w-full h-14 rounded-xl border border-border/30 bg-card/20 px-4 flex items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        <ShimmerBase className="h-6 w-24 rounded-full" />
        <ShimmerBase className="h-4 w-64 sm:w-96 rounded" />
      </div>
      <ShimmerBase className="h-4 w-16 rounded hidden sm:block" />
    </div>
  );
});

/**
 * NewsletterSkeleton — 1:1 Mirror for Newsletter Spatial Object
 */
export const NewsletterSkeleton = React.memo(function NewsletterSkeleton() {
  return (
    <div className="w-full rounded-3xl border border-border/40 bg-gradient-to-r from-card/60 via-card/30 to-card/60 p-8 sm:p-12 text-center flex flex-col items-center justify-center space-y-6">
      <ShimmerBase className="w-12 h-12 rounded-2xl" />
      <div className="space-y-2 max-w-md w-full flex flex-col items-center">
        <ShimmerBase className="h-8 w-64 rounded-md" />
        <ShimmerBase className="h-4 w-full rounded" />
        <ShimmerBase className="h-4 w-4/5 rounded" />
      </div>
      <div className="flex flex-col sm:flex-row gap-3 w-full max-w-md">
        <ShimmerBase className="h-11 flex-1 rounded-xl" />
        <ShimmerBase className="h-11 w-32 rounded-xl" />
      </div>
    </div>
  );
});
