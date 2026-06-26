"use client";

import React from "react";
import { Folder, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { usePersonalization } from "@/components/providers/PersonalizationProvider";
import { cn } from "@/lib/utils";

export function CollectionsList({ compact = false }: { compact?: boolean }) {
  const { collections, bookmarkedArticles } = usePersonalization();

  return (
    <div className={cn("space-y-4", !compact && "rounded-lg border bg-card p-6")}>
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-lg">My Collections</h3>
          {!compact && <p className="text-sm text-muted-foreground">Organize your saved articles into collections</p>}
        </div>
        <Button variant="outline" size="sm" className="gap-2">
          <Plus className="h-4 w-4" />
          <span>New</span>
        </Button>
      </div>

      {collections.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-8 text-center bg-muted/20 border border-dashed rounded-md">
          <Folder className="h-8 w-8 text-muted-foreground mb-3" />
          <p className="text-sm font-medium text-foreground">No collections yet</p>
          <p className="text-xs text-muted-foreground mt-1 max-w-[200px]">
            Create collections to organize your saved articles by topic or project.
          </p>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
          {collections.map(collection => {
            const articleCount = bookmarkedArticles.filter(b => b.collectionId === collection.id).length;
            return (
              <div 
                key={collection.id} 
                className="group relative flex flex-col gap-2 rounded-md border p-4 hover:border-primary/50 transition-colors cursor-pointer bg-background"
              >
                <div className="flex items-center gap-2">
                  <div 
                    className="h-3 w-3 rounded-full shrink-0" 
                    style={{ backgroundColor: collection.color || "hsl(var(--primary))" }}
                  />
                  <h4 className="font-medium text-sm line-clamp-1">{collection.name}</h4>
                </div>
                <div className="flex items-center justify-between mt-auto">
                  <span className="text-xs text-muted-foreground">{articleCount} articles</span>
                  <span className="text-[10px] text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">
                    View
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
