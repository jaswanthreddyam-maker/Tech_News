import React from "react";
import { Container } from "@/components/layout/Container";
import { ShimmerBase } from "@/components/skeletons/ShimmerBase";

export default function EntityLoading() {
  return (
    <Container size="default" className="py-12">
      {/* Header Skeleton */}
      <div className="mb-12 border-b border-neutral-800 pb-8 space-y-4">
        <div className="flex items-center gap-4">
          <ShimmerBase className="w-16 h-16 rounded-xl shrink-0" />
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <ShimmerBase className="h-4 w-24 rounded" />
              <ShimmerBase className="h-7 w-20 rounded-full" />
            </div>
            <ShimmerBase className="h-10 w-64 md:w-80 rounded-xl" />
          </div>
        </div>

        <div className="space-y-2 max-w-3xl pt-2">
          <ShimmerBase className="h-5 w-full rounded" />
          <ShimmerBase className="h-5 w-3/4 rounded" />
        </div>
      </div>

      {/* Grid: Main + Sidebar */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
        {/* Main Content (col-span-2) */}
        <div className="lg:col-span-2 space-y-12">
          {/* Latest News Section Skeleton */}
          <section className="space-y-6">
            <div className="border-b border-neutral-800 pb-3">
              <ShimmerBase className="h-6 w-36 rounded-md" />
            </div>
            
            <div className="space-y-6">
              {[1, 2, 3].map((i) => (
                <div key={i} className="space-y-2">
                  <ShimmerBase className="h-6 w-4/5 rounded-md" />
                  <ShimmerBase className="h-4 w-full rounded" />
                  <ShimmerBase className="h-4 w-2/3 rounded" />
                  <div className="flex items-center gap-2 pt-1">
                    <ShimmerBase className="h-3 w-16 rounded" />
                    <ShimmerBase className="h-3 w-24 rounded" />
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Timeline Section Skeleton */}
          <section className="space-y-6">
            <div className="border-b border-neutral-800 pb-3">
              <ShimmerBase className="h-6 w-28 rounded-md" />
            </div>

            <div className="relative border-l-2 border-neutral-800 ml-3 space-y-8 py-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="relative pl-6 space-y-2">
                  <div className="absolute -left-[9px] top-1.5 w-4 h-4 bg-neutral-900 border-2 border-neutral-700 rounded-full" />
                  <ShimmerBase className="h-4 w-24 rounded" />
                  <ShimmerBase className="h-4 w-5/6 rounded" />
                  <ShimmerBase className="h-5 w-16 rounded" />
                </div>
              ))}
            </div>
          </section>
        </div>

        {/* Sidebar (col-span-1) */}
        <div className="space-y-8">
          {/* Entity Overview Stats Card */}
          <div className="bg-neutral-900/60 p-6 rounded-xl border border-neutral-800 space-y-4">
            <ShimmerBase className="h-4 w-28 rounded" />
            <div className="space-y-3">
              <div className="space-y-1">
                <ShimmerBase className="h-3 w-20 rounded" />
                <ShimmerBase className="h-8 w-16 rounded" />
              </div>
              <div className="space-y-1">
                <ShimmerBase className="h-3 w-16 rounded" />
                <ShimmerBase className="h-4 w-24 rounded" />
              </div>
            </div>
          </div>

          {/* Graph Network Relationships Card */}
          <div className="bg-neutral-900/60 p-6 rounded-xl border border-neutral-800 space-y-4">
            <ShimmerBase className="h-4 w-32 rounded" />
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="border-b border-neutral-800 pb-3 last:border-0 last:pb-0 space-y-1">
                  <ShimmerBase className="h-4 w-full rounded" />
                </div>
              ))}
            </div>
          </div>

          {/* Related Companies Card */}
          <div className="bg-neutral-900/60 p-6 rounded-xl border border-neutral-800 space-y-4">
            <ShimmerBase className="h-4 w-36 rounded" />
            <div className="flex flex-wrap gap-2">
              <ShimmerBase className="h-7 w-20 rounded-full" />
              <ShimmerBase className="h-7 w-24 rounded-full" />
              <ShimmerBase className="h-7 w-16 rounded-full" />
              <ShimmerBase className="h-7 w-28 rounded-full" />
            </div>
          </div>
        </div>
      </div>
    </Container>
  );
}
