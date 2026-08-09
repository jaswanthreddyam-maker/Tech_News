import { Skeleton } from "@/design-system/components/Skeleton";
import { TRENDING_LAYOUT } from "./constants";

export function StorySkeleton() {
  return (
    <section className="py-8 my-6 w-full">
      {/* Header Skeleton */}
      <div className="flex items-center gap-3 mb-9">
        <Skeleton className="w-8 h-8 rounded-xl" />
        <div>
          <Skeleton className="h-7 w-48 mb-1" />
          <Skeleton className="h-3 w-72" />
        </div>
      </div>

      {/* Grid Skeleton (Using TRENDING_LAYOUT constants) */}
      <div
        className="grid grid-cols-1 lg:grid-cols-12 gap-6 w-full mx-auto"
        style={{ maxWidth: `${TRENDING_LAYOUT.MAX_WIDTH}px` }}
      >
        <div className="lg:col-span-5 flex flex-col h-[460px]">
          <Skeleton className="w-full h-full rounded-[18px]" />
        </div>
        <div className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-6">
          {Array.from({ length: TRENDING_LAYOUT.MAX_COMPACT }).map((_, i) => (
            <Skeleton key={i} className="w-full h-[140px] rounded-[16px]" />
          ))}
        </div>
      </div>
    </section>
  );
}
