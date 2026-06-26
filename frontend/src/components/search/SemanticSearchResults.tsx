"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { SemanticResultCard } from "./SemanticResultCard";
import { SearchEmptyState } from "./SearchEmptyState";
import { SearchFilters as ISearchFilters } from "@/lib/api/search/types";
import { Loader2 } from "lucide-react";
import { Skeleton } from "@/design-system/components/Skeleton";
import { useLoadingState } from "@/design-system/hooks/useLoadingState";
import { fetchKeywordSearch } from "@/lib/api/search/keyword";
import { SemanticSearchResult } from "@/lib/api/search/types";
import { ErrorState } from "@/components/common/ErrorState";

interface Props {
  query: string;
  filters: ISearchFilters;
}

export function SemanticSearchResults({ query, filters }: Props) {
  const { data, isPending, isError, isFetching } = useQuery<SemanticSearchResult[]>({
    queryKey: ["semanticSearch", query, filters],
    queryFn: async () => {
      // With the new API, both semantic and keyword use the unified /search endpoint
      return fetchKeywordSearch(query, filters, 20);
    },
    placeholderData: keepPreviousData,
    enabled: query.length > 0,
  });

  const loadingLevel = useLoadingState(isPending);

  if (!query) {
    return null;
  }

  if (isError) {
    return (
      <ErrorState title="Search Failed" description="Could not complete your search request. Please try again." />
    );
  }

  if (isPending) {
    return (
      <div className="space-y-6 relative">
        <div className="absolute -top-12 right-0 flex items-center gap-2 text-xs text-muted-foreground">
          <Loader2 className="w-3 h-3 animate-spin" />
          Searching...
        </div>
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex flex-col md:flex-row gap-6 p-6 rounded-xl border border-border/50 bg-card/30">
            <div className="flex-1 space-y-4">
              <Skeleton level={loadingLevel} className="h-5 w-24 rounded-full" />
              <Skeleton level={loadingLevel} className="h-6 w-3/4" />
              <div className="space-y-2">
                <Skeleton level={loadingLevel} className="h-4 w-full" />
                <Skeleton level={loadingLevel} className="h-4 w-5/6" />
              </div>
              <div className="flex gap-4 pt-2">
                <Skeleton level={loadingLevel} className="h-3 w-16" />
                <Skeleton level={loadingLevel} className="h-3 w-24" />
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!data || data.length === 0) {
    return <SearchEmptyState />;
  }

  return (
    <div className="space-y-6 relative">
      {isFetching && (
        <div className="absolute -top-12 right-0 flex items-center gap-2 text-xs text-muted-foreground">
          <Loader2 className="w-3 h-3 animate-spin" />
          Updating results...
        </div>
      )}
      
      {data.map((result) => (
        <SemanticResultCard key={`${result.type}-${result.id}`} result={result} />
      ))}
    </div>
  );
}
