"use client";

import React, { useState } from "react";
import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { usePersonalization, ReadingHistoryItem } from "@/components/providers/PersonalizationProvider";
import { EmptyState, EmptyIllustration, EmptyAction } from "@/components/common/EmptyState";
import { History, Clock, CheckCircle2, BookOpen, Trash2, X, ExternalLink } from "lucide-react";

export function ReadingHistoryList() {
  const { readingHistory, removeHistoryItem, clearHistory } = usePersonalization();
  const [showClearConfirm, setShowClearConfirm] = useState(false);

  if (readingHistory.length === 0) {
    return (
      <EmptyState size="lg">
        <EmptyIllustration
          icon={History}
          title="No reading history"
          description="Articles you read will appear here."
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

  const formatReadingDuration = (seconds: number) => {
    if (!seconds || seconds < 60) {
      return `${seconds || 0}s read`;
    }
    const mins = Math.floor(seconds / 60);
    const remainingSecs = seconds % 60;
    return remainingSecs > 0 ? `${mins}m ${remainingSecs}s read` : `${mins}m read`;
  };

  const formatTimestamp = (timestamp: number) => {
    try {
      return formatDistanceToNow(new Date(timestamp), { addSuffix: true });
    } catch {
      return "recently";
    }
  };

  return (
    <div className="space-y-6">
      {/* Header controls */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-2 border-b border-border/40">
        <p className="text-sm font-mono text-muted-foreground">
          {readingHistory.length} {readingHistory.length === 1 ? "article" : "articles"} in your history
        </p>

        {showClearConfirm ? (
          <div className="flex items-center gap-2 bg-destructive/10 border border-destructive/20 px-3 py-1.5 rounded-xl">
            <span className="text-xs text-destructive font-medium">Clear entire history?</span>
            <button
              onClick={() => {
                clearHistory();
                setShowClearConfirm(false);
              }}
              className="text-xs bg-destructive text-destructive-foreground px-2 py-1 rounded-md hover:bg-destructive/90 transition-colors font-semibold cursor-pointer"
            >
              Yes, Clear
            </button>
            <button
              onClick={() => setShowClearConfirm(false)}
              className="text-xs text-muted-foreground hover:text-foreground px-2 py-1 rounded-md transition-colors cursor-pointer"
            >
              Cancel
            </button>
          </div>
        ) : (
          <button
            onClick={() => setShowClearConfirm(true)}
            className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-destructive transition-colors font-mono uppercase tracking-wider cursor-pointer"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Clear History</span>
          </button>
        )}
      </div>

      {/* History List */}
      <div className="space-y-3">
        {readingHistory.map((item: ReadingHistoryItem) => (
          <div
            key={item.articleId}
            className="group relative flex flex-col md:flex-row md:items-center justify-between p-4 bg-card/60 hover:bg-card border border-border/50 hover:border-border rounded-xl transition-all gap-4"
          >
            <div className="space-y-1.5 flex-1 min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-[10px] font-mono uppercase tracking-widest text-primary font-semibold">
                  {item.source || "Tech News Today"}
                </span>
                {item.topic && (
                  <span className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground bg-muted/50 px-2 py-0.5 rounded-full">
                    {item.topic}
                  </span>
                )}
                <span className="text-xs text-muted-foreground font-mono">
                  • {formatTimestamp(item.lastReadAt || item.openedAt)}
                </span>
              </div>

              <Link
                href={`/articles/${item.slug || item.articleId}`}
                className="text-base font-semibold text-foreground group-hover:text-primary transition-colors block line-clamp-2"
              >
                {item.title}
              </Link>
            </div>

            <div className="flex items-center gap-4 shrink-0 self-end md:self-center">
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center gap-1 text-xs font-mono text-muted-foreground bg-background/50 border border-border/40 px-2.5 py-1 rounded-lg">
                  <Clock className="w-3.5 h-3.5 text-emerald-500" />
                  {formatReadingDuration(item.readingTime)}
                </span>

                {item.completed ? (
                  <span className="inline-flex items-center gap-1 text-xs font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-lg">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Finished
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-xs font-mono text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2.5 py-1 rounded-lg">
                    <BookOpen className="w-3.5 h-3.5" />
                    In Progress
                  </span>
                )}
              </div>

              <div className="flex items-center gap-1 border-l border-border/40 pl-3">
                <Link
                  href={`/articles/${item.slug || item.articleId}`}
                  title="Read Article"
                  className="p-1.5 rounded-lg text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors"
                >
                  <ExternalLink className="w-4 h-4" />
                </Link>

                <button
                  onClick={() => removeHistoryItem(item.articleId)}
                  title="Remove from history"
                  className="p-1.5 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
