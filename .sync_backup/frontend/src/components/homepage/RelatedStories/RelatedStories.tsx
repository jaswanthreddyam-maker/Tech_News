"use client";

import { useRecommendations } from "@/hooks/useRecommendations";
import { AsyncResource, AsyncResourceState } from "@/components/ui/AsyncResource";
import { RecommendedArticle } from "@/lib/api/recommendations/types";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import Link from "next/link";

import { Reveal } from "@/components/animations";

export function RelatedStories() {
  const enabled = process.env.NEXT_PUBLIC_FF_CONTINUE_READING !== "false";
  const { data, isLoading, isError, error, refetch } = useRecommendations({ limit: 4, enabled });

  if (!enabled) return null;

  const resourceState: AsyncResourceState<RecommendedArticle[]> = {
    state: isLoading ? "loading" : isError ? "error" : (!data || data.length === 0) ? "empty" : "success",
    data,
    error,
    retry: refetch,
  };

  return (
    <Reveal>
      <div className="bg-card border border-border p-6 rounded-lg">
        <h3 className="font-sans font-bold mb-4">Continue Reading</h3>
        <AsyncResource
          resource={resourceState}
          loading={
            <div className="space-y-4">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
            </div>
          }
          empty={<p className="text-sm text-muted-foreground">No recommendations available yet.</p>}
          error={
            <div className="text-sm">
              <p className="mb-2">Unable to load recommendations.</p>
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                Retry
              </Button>
            </div>
          }
        >
          {(articles) => (
            <div className="space-y-4">
              {articles.map((article) => (
                <div key={article.id} className="group">
                  <Link href={`/articles/${article.slug}`} className="block">
                    <h4 className="text-sm font-medium group-hover:text-primary transition-colors line-clamp-2 mb-1">
                      {article.title}
                    </h4>
                    <div className="flex items-center text-xs text-muted-foreground space-x-2">
                      <span className="truncate">{article.source_name}</span>
                      {article.reasons && article.reasons.length > 0 && (
                        <>
                          <span>•</span>
                          <span className="text-primary/80">{article.reasons[0].label}</span>
                        </>
                      )}
                    </div>
                  </Link>
                </div>
              ))}
            </div>
          )}
        </AsyncResource>
      </div>
    </Reveal>
  );
}
