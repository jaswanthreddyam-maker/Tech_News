"use client";

import React from "react";
import { Search, BellRing, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { usePersonalization } from "@/components/providers/PersonalizationProvider";
import { cn } from "@/lib/utils";
import Link from "next/link";

export function SavedSearchesList({ compact = false }: { compact?: boolean }) {
  const { savedSearches } = usePersonalization();

  return (
    <div className={cn("space-y-4", !compact && "rounded-lg border bg-card p-6")}>
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-lg">Saved Searches</h3>
          {!compact && <p className="text-sm text-muted-foreground">Monitor specific topics with automated alerts</p>}
        </div>
      </div>

      {savedSearches.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-8 text-center bg-muted/20 border border-dashed rounded-md">
          <Search className="h-8 w-8 text-muted-foreground mb-3" />
          <p className="text-sm font-medium text-foreground">No saved searches</p>
          <p className="text-xs text-muted-foreground mt-1 max-w-[200px]">
            Save a search to get notified when new articles match your query.
          </p>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {savedSearches.map(search => (
            <div 
              key={search.query + search.savedAt} 
              className="group relative flex flex-col gap-3 rounded-md border p-4 bg-background"
            >
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <h4 className="font-medium text-sm line-clamp-1">&quot;{search.query}&quot;</h4>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1"><Clock className="h-3 w-3" /> Daily</span>
                    <span className="flex items-center gap-1"><BellRing className="h-3 w-3" /> Active</span>
                  </div>
                </div>
                <Button variant="ghost" size="sm" asChild className="h-7 text-xs px-2 shrink-0">
                  <Link href={`/search?q=${encodeURIComponent(search.query)}`}>
                    View Results
                  </Link>
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
