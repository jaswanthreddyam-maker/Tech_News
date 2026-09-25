"use client";

import React, { useEffect, useState } from "react";
import { usePersonalization } from "@/components/providers/PersonalizationProvider";
import { StoryCard } from "@/components/common/StoryCard";
import { EmptyState, EmptyIllustration, EmptyAction } from "@/components/common/EmptyState";
import { Bookmark, Loader2, BookmarkX } from "lucide-react";
import Link from "next/link";
import { apiFetch } from "@/lib/api/client";
import { Article, PaginatedResponse } from "@/lib/api/types";

export function BookmarkList({ limit }: { limit?: number }) {
  const { bookmarkedArticles, toggleBookmark } = usePersonalization();
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (bookmarkedArticles.length === 0) {
      setArticles([]);
      setLoading(false);
      return;
    }

    const idsToFetch = limit
      ? bookmarkedArticles.slice(0, limit).map((b) => b.articleId)
      : bookmarkedArticles.map((b) => b.articleId);

    const fetchBookmarks = async () => {
      setLoading(true);
      try {
        const res = await apiFetch<PaginatedResponse<Article>>("/news", {
          params: { ids: idsToFetch.join(",") },
        });
        const list = res?.data || [];
        setArticles(list);
      } catch (err) {
        // Fallback: If news?ids fails, show empty
        setArticles([]);
      } finally {
        setLoading(false);
      }
    };

    fetchBookmarks();
  }, [bookmarkedArticles, limit]);

  if (loading) {
    return (
      <div className="flex justify-center items-center py-16">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (bookmarkedArticles.length === 0 || articles.length === 0) {
    return (
      <EmptyState>
        <EmptyIllustration
          icon={Bookmark}
          title="Nothing saved yet"
          description="Save articles to build your reading list."
        />
        <EmptyAction
          primaryAction={
            <Link
              href="/"
              className="px-4 py-2 bg-primary text-primary-foreground rounded-full text-sm font-medium hover:bg-primary/90 transition-colors inline-block"
            >
              Explore News
            </Link>
          }
        />
      </EmptyState>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-sm font-mono text-muted-foreground">
          {articles.length} {articles.length === 1 ? "article" : "articles"} saved
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {articles.map((article) => (
          <div key={article.id} className="relative group/card">
            <StoryCard article={article} />
            <button
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                toggleBookmark(Number(article.id));
              }}
              title="Remove from bookmarks"
              className="absolute top-3 right-3 p-2 rounded-lg bg-background/80 backdrop-blur-md border border-border/50 text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all opacity-0 group-hover/card:opacity-100 z-20 cursor-pointer shadow-sm"
            >
              <BookmarkX className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
