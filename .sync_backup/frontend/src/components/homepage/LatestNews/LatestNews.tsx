"use client";

import { useLatestInfinite } from "@/components/hooks/articles/useArticles";
import { Skeleton } from "@/components/ui/skeleton";
import Link from "next/link";
import { Clock, Loader2 } from "lucide-react";
import React, { useEffect, useRef } from "react";
import { useInView } from "react-intersection-observer";
import { useWindowVirtualizer } from "@tanstack/react-virtual";
import { ArticleThumbnail } from "@/components/common/ArticleThumbnail";
import { Reveal, StaggerContainer, StaggerItem } from "@/components/animations";

export function LatestNews() {
  const { data, isLoading, error, fetchNextPage, hasNextPage, isFetchingNextPage } = useLatestInfinite();
  const { ref, inView } = useInView();
  const listRef = useRef<HTMLDivElement>(null);

  const allArticles = data?.pages.flatMap((page) => page.data) || [];
  const useVirtualizer = allArticles.length >= 80;

  // We conditionally call useWindowVirtualizer. Hooks must be called unconditionally,
  // but we can pass an empty count if not using it to minimize overhead, or just use it.
  const virtualizer = useWindowVirtualizer({
    count: useVirtualizer ? allArticles.length : 0,
    estimateSize: () => 180, // estimated pixel height of an article row
    overscan: 5,
    scrollMargin: listRef.current?.offsetTop ?? 0,
  });

  useEffect(() => {
    if (inView && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [inView, hasNextPage, isFetchingNextPage, fetchNextPage]);

  if (isLoading) return <Skeleton className="w-full h-[800px]" />;
  if (error) return (
    <div className="py-8 flex justify-center text-red-500">
      Error loading latest intelligence.
    </div>
  );
  if (!data || !data.pages || !data.pages[0] || !data.pages[0].data || data.pages[0].data.length === 0) return (
    <div className="py-8 flex justify-center text-muted-foreground">
      No recent intelligence available.
    </div>
  );

  const renderArticle = (article: any, index: number) => (
    <StaggerItem key={article.id || index}>
      <Link 
        href={`/articles/${article.slug}`} 
        className="group grid grid-cols-1 md:grid-cols-4 gap-6 p-4 -mx-4 rounded-xl hover:bg-neutral-900/30 transition-colors"
      >
        {/* Thumbnail */}
        <ArticleThumbnail
          article={article}
          className="md:col-span-1 aspect-video"
          imgClassName="object-cover group-hover:scale-105 transition-transform duration-500"
          sizes="(max-width: 768px) 100vw, 25vw"
        />

        {/* Content */}
        <div className="md:col-span-3 flex flex-col justify-center">
          <div className="flex items-center gap-3 text-[10px] font-mono uppercase tracking-wider text-muted-foreground mb-2">
            <span className="text-primary">{article.category}</span>
            <span>|</span>
            <span>{article.source}</span>
          </div>
          <h3 className="text-xl font-serif font-bold leading-snug group-hover:text-primary transition-colors mb-2">
            {article.title}
          </h3>
          <p className="text-muted-foreground text-sm line-clamp-2 mb-3">
            {article.summary}
          </p>
          <div className="flex items-center gap-2 text-xs text-muted-foreground mt-auto">
            <Clock className="w-3.5 h-3.5" />
            <span>{new Date(article.published_at).toLocaleString()}</span>
          </div>
        </div>
      </Link>
    </StaggerItem>
  );

  return (
    <section>
      <Reveal>
        <div className="flex items-center gap-3 mb-8">
          <h2 className="text-2xl font-sans font-bold tracking-tight">Latest Intelligence</h2>
        </div>
      </Reveal>

      <StaggerContainer ref={listRef} className="flex flex-col gap-6" style={useVirtualizer ? { height: `${virtualizer.getTotalSize()}px`, position: 'relative' } : undefined}>
        {useVirtualizer ? (
          virtualizer.getVirtualItems().map((virtualItem) => (
            <div
              key={virtualItem.key}
              data-index={virtualItem.index}
              ref={virtualizer.measureElement}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                transform: `translateY(${virtualItem.start}px)`,
              }}
            >
              {renderArticle(allArticles[virtualItem.index], virtualItem.index)}
            </div>
          ))
        ) : (
          allArticles.map((article, i) => renderArticle(article, i))
        )}
      </StaggerContainer>

      {/* Intersection Observer Target */}
      <div ref={ref} className="w-full py-8 flex justify-center">
        {isFetchingNextPage ? (
          <div className="flex items-center gap-2 text-muted-foreground font-mono text-xs uppercase tracking-widest">
            <Loader2 className="w-4 h-4 animate-spin" /> Fetching Archive...
          </div>
        ) : hasNextPage ? (
          <div className="text-muted-foreground font-mono text-xs uppercase tracking-widest">
            Scroll for more
          </div>
        ) : (
          <div className="text-muted-foreground font-mono text-xs uppercase tracking-widest opacity-50">
            End of Intelligence Feed
          </div>
        )}
      </div>
    </section>
  );
}
