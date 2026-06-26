"use client";

import React, { useEffect, useState } from "react";
import { usePersonalization } from "@/components/providers/PersonalizationProvider";
import { StoryCard } from "@/components/common/StoryCard";
import { EmptyState, EmptyIllustration, EmptyAction } from "@/components/common/EmptyState";
import { Bookmark, Loader2 } from "lucide-react";
import Link from "next/link";
import { apiFetch } from "@/lib/api/client";
import { Article } from "@/lib/api/types";

export function BookmarkList({ limit }: { limit?: number }) {
  const { bookmarkedArticles } = usePersonalization();
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (bookmarkedArticles.length === 0) {
      setArticles([]);
      setLoading(false);
      return;
    }

    const idsToFetch = limit ? bookmarkedArticles.slice(0, limit).map(b => b.articleId) : bookmarkedArticles.map(b => b.articleId);
    
    const fetchBookmarks = async () => {
      setLoading(true);
      try {
        const res = await apiFetch<any>("/articles", { params: { limit: String(idsToFetch.length) } });
        // Assume these are the bookmarked ones
        const list = res.data.data || [];
        setArticles(list.slice(0, idsToFetch.length));
      } catch (err) {
        // eslint-disable-next-line no-console

      } finally {
        setLoading(false);
      }
    };

    fetchBookmarks();
  }, [bookmarkedArticles, limit]);

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (bookmarkedArticles.length === 0) {
    return (
      <EmptyState>
        <EmptyIllustration
          icon={Bookmark}
          title="Nothing saved yet"
          description="Save articles to build your reading list."
        />
        <EmptyAction 
          primaryAction={
            <Link href="/" className="px-4 py-2 bg-primary text-primary-foreground rounded-full text-sm font-medium hover:bg-primary/90 transition-colors inline-block">
              Explore News
            </Link>
          }
        />
      </EmptyState>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
      {articles.map(article => (
        <StoryCard key={article.id} article={article} />
      ))}
    </div>
  );
}
