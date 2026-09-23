import React from "react";
import { ShimmerBase } from "@/components/skeletons/ShimmerBase";

export function SearchPageSkeleton() {
  return (
    <div className="max-w-screen-2xl mx-auto px-4 md:px-6 py-8 md:py-12 space-y-8">
      {/* Search Header */}
      <div className="max-w-3xl mx-auto text-center space-y-4 mb-12">
        <ShimmerBase className="h-10 md:h-12 w-64 md:w-80 mx-auto rounded-xl" />
        <ShimmerBase className="h-5 w-72 md:w-96 mx-auto rounded-md" />
        
        {/* Search Input Pill */}
        <div className="relative mt-8 max-w-2xl mx-auto">
          <div className="w-full h-14 rounded-full border border-border/40 bg-card/30 flex items-center px-6 gap-4">
            <ShimmerBase className="w-5 h-5 rounded-full shrink-0" />
            <ShimmerBase className="w-48 h-5 rounded-md" />
          </div>
        </div>
      </div>

      {/* Main Grid: Filters + Results */}
      <div className="flex flex-col lg:flex-row gap-8">
        {/* Filters Sidebar */}
        <aside className="w-full lg:w-64 shrink-0 space-y-6">
          <div className="sticky top-20 bg-card/30 p-6 rounded-xl border border-border/40 space-y-6">
            <ShimmerBase className="h-6 w-24 rounded-md" />
            
            {/* Filter group 1 */}
            <div className="space-y-3">
              <ShimmerBase className="h-4 w-28 rounded" />
              <div className="space-y-2">
                <ShimmerBase className="h-8 w-full rounded-lg" />
                <ShimmerBase className="h-8 w-full rounded-lg" />
                <ShimmerBase className="h-8 w-full rounded-lg" />
              </div>
            </div>

            {/* Filter group 2 */}
            <div className="space-y-3">
              <ShimmerBase className="h-4 w-20 rounded" />
              <div className="flex flex-wrap gap-2">
                <ShimmerBase className="h-7 w-16 rounded-full" />
                <ShimmerBase className="h-7 w-20 rounded-full" />
                <ShimmerBase className="h-7 w-14 rounded-full" />
              </div>
            </div>

            {/* Filter group 3 */}
            <div className="space-y-3">
              <ShimmerBase className="h-4 w-32 rounded" />
              <ShimmerBase className="h-2 w-full rounded-full" />
            </div>
          </div>
        </aside>

        {/* Results Area */}
        <div className="flex-1 min-w-0 space-y-6">
          {/* Explanation badge skeleton */}
          <div className="flex items-center gap-3">
            <ShimmerBase className="h-6 w-36 rounded-full" />
            <ShimmerBase className="h-4 w-48 rounded" />
          </div>

          {/* Result Card Skeletons */}
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="flex flex-col md:flex-row gap-6 p-4 md:p-6 rounded-xl border border-border/40 bg-card/30"
            >
              <div className="flex-1 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <ShimmerBase className="w-4 h-4 rounded" />
                    <ShimmerBase className="h-4 w-20 rounded" />
                  </div>
                  <ShimmerBase className="h-4 w-24 rounded" />
                </div>

                <div className="space-y-2">
                  <ShimmerBase className="h-6 w-3/4 rounded-md" />
                  <ShimmerBase className="h-4 w-full rounded" />
                  <ShimmerBase className="h-4 w-5/6 rounded" />
                </div>

                <div className="flex gap-4 pt-2">
                  <ShimmerBase className="h-4 w-20 rounded" />
                  <ShimmerBase className="h-4 w-28 rounded" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function Loading() {
  return <SearchPageSkeleton />;
}
