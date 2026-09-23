import React from "react";
import { ShimmerBase } from "@/components/skeletons/ShimmerBase";

export default function DashboardLoading() {
  return (
    <div className="container mx-auto px-4 py-12 flex flex-col lg:flex-row gap-12 mt-16">
      {/* Sidebar Navigation Skeleton */}
      <aside className="w-full lg:w-64 shrink-0">
        <div className="sticky top-24">
          <div className="mb-8 space-y-2">
            <ShimmerBase className="h-9 w-36 rounded-lg" />
            <ShimmerBase className="h-4 w-48 rounded-md" />
          </div>

          <div className="flex flex-col gap-1">
            {[
              { w: "w-20" },
              { w: "w-28" },
              { w: "w-24" },
              { w: "w-32" },
              { w: "w-32" },
              { w: "w-24" },
              { w: "w-20" },
            ].map((item, idx) => (
              <div
                key={idx}
                className="flex items-center gap-3 px-4 py-3 rounded-lg w-full"
              >
                <ShimmerBase className="w-5 h-5 rounded-md shrink-0" />
                <ShimmerBase className={`h-4 ${item.w} rounded`} />
              </div>
            ))}
          </div>
        </div>
      </aside>

      {/* Main Content Area Skeleton */}
      <main className="flex-1 min-w-0 border border-border/50 bg-card/20 rounded-2xl p-6 lg:p-12 space-y-12">
        {/* Welcome Section */}
        <section className="space-y-6">
          <ShimmerBase className="h-8 w-44 rounded-lg" />
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Widget 1 */}
            <div className="p-6 rounded-xl border border-border/40 bg-card/30 space-y-4">
              <div className="flex items-center justify-between">
                <ShimmerBase className="h-5 w-32 rounded" />
                <ShimmerBase className="w-5 h-5 rounded" />
              </div>
              <ShimmerBase className="h-10 w-24 rounded-lg" />
              <ShimmerBase className="h-24 w-full rounded-lg" />
            </div>

            {/* Widget 2 */}
            <div className="p-6 rounded-xl border border-border/40 bg-card/30 space-y-4">
              <div className="flex items-center justify-between">
                <ShimmerBase className="h-5 w-36 rounded" />
                <ShimmerBase className="w-5 h-5 rounded" />
              </div>
              <div className="space-y-3 pt-2">
                <ShimmerBase className="h-4 w-full rounded" />
                <ShimmerBase className="h-4 w-5/6 rounded" />
                <ShimmerBase className="h-4 w-4/5 rounded" />
              </div>
            </div>
          </div>
        </section>

        {/* Recent Bookmarks Section */}
        <section className="space-y-6">
          <ShimmerBase className="h-7 w-48 rounded-lg" />
          
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="p-4 rounded-xl border border-border/40 bg-card/30 flex gap-4 items-center"
              >
                <ShimmerBase className="w-20 h-14 rounded-lg shrink-0" />
                <div className="flex-1 space-y-2">
                  <ShimmerBase className="h-5 w-3/4 rounded" />
                  <ShimmerBase className="h-3 w-1/3 rounded" />
                </div>
                <ShimmerBase className="w-8 h-8 rounded-full shrink-0" />
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
