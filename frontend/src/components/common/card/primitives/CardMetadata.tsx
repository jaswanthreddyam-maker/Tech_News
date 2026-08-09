"use client";

import React from "react";
import { Clock, User } from "lucide-react";
import { PresentationMetadataFlags } from "@/domains/article/presentation";

interface CardMetadataProps {
  publishedAt?: string | null;
  readTime?: number | null;
  flags?: PresentationMetadataFlags;
  authorName?: string | null;
  className?: string;
}

export function CardMetadata({
  publishedAt,
  readTime,
  flags,
  authorName,
  className = "",
}: CardMetadataProps) {
  const showReadingTime = flags?.showReadingTime ?? true;
  const showUrgency = flags?.showUrgency ?? false;
  const showAuthor = flags?.showAuthorByline ?? false;

  return (
    <div className={`flex flex-wrap items-center gap-3 text-xs font-mono text-muted-foreground/80 ${className}`}>
      {showUrgency && (
        <div className="flex items-center gap-1.5 text-rose-400 font-bold uppercase tracking-wider text-[10px]">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
          </span>
          Live
        </div>
      )}

      {showAuthor && authorName && (
        <div className="flex items-center gap-1 text-foreground/90 font-medium">
          <User className="w-3 h-3 text-amber-400" />
          <span>{authorName}</span>
        </div>
      )}

      {publishedAt && (
        <time dateTime={publishedAt} suppressHydrationWarning>
          {new Date(publishedAt).toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            timeZone: "UTC",
          })}
        </time>
      )}

      {showReadingTime && readTime && (
        <div className="flex items-center gap-1">
          <Clock className="w-3 h-3 text-muted-foreground/60" />
          <span>{readTime}m read</span>
        </div>
      )}
    </div>
  );
}
