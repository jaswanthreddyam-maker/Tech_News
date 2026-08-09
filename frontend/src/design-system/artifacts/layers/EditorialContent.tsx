import React from 'react';
import { ArticleThumbnail } from '@/components/common/ArticleThumbnail';

/**
 * EditorialContent
 * "What information exists?"
 * 
 * Pure data. No layout, no spacing, no typography sizes.
 * These are headless content primitives. The Surface layer is 
 * responsible for formatting and positioning them.
 */

export function ContentTitle({ title, className }: { title?: string, className?: string }) {
  return <span className={className}>{title || "Untitled Article"}</span>;
}

export function ContentSummary({ summary, className }: { summary?: string, className?: string }) {
  if (!summary) return null;
  return <span className={className}>{summary}</span>;
}

export function ContentSource({ source, className }: { source: string, className?: string }) {
  return <span className={className}>{source}</span>;
}

export function ContentDate({ date, className }: { date?: string | null, className?: string }) {
  if (!date) return <span className={className}>Just Now</span>;
  const parsed = new Date(date);
  if (isNaN(parsed.getTime())) return <span className={className}>Just Now</span>;
  return (
    <span suppressHydrationWarning className={className}>
      {parsed.toLocaleDateString('en-US', { timeZone: 'UTC' })}
    </span>
  );
}

export function ContentThumbnail({ article, className }: { article: any, className?: string }) {
  // We use the common ArticleThumbnail here, but strip it of layout responsibilities
  // The Surface layer must pass the positioning and aspect ratio via className
  return (
    <ArticleThumbnail
      article={article}
      className={className}
      imgClassName="object-cover transition-opacity duration-700"
      sizes="(max-width: 1024px) 100vw, 33vw"
    />
  );
}
