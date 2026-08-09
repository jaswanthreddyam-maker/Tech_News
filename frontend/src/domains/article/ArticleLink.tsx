"use client";

import React, { useState, useRef, useEffect, useCallback, forwardRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { CanonicalArticle } from "./types";
import { resolveArticleRoute, reportNavigationError, trackArticleClick } from "../navigation";

export interface ArticleLinkProps {
  article: CanonicalArticle;
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
  section?: string;
  position?: number;
  prefetchPriority?: boolean;
  onClick?: (e: React.MouseEvent) => void;
  onPointerDown?: (e: React.PointerEvent) => void;
  onPointerMove?: (e: React.PointerEvent) => void;
  onPointerUp?: (e: React.PointerEvent) => void;
}

/**
 * ArticleLink — Single Navigation Owner for Article Cards
 * 
 * Encapsulates routing, 150ms intent-debounced prefetching, telemetry reporting,
 * and accessibility for all article link entry points across the application.
 */
export const ArticleLink = forwardRef<HTMLElement, ArticleLinkProps>(function ArticleLink(
  {
    article,
    children,
    className = "",
    style,
    section = "DefaultSection",
    position = 0,
    prefetchPriority = false,
    onClick,
    onPointerDown,
    onPointerMove,
    onPointerUp,
  },
  ref
) {
  const router = useRouter();
  const route = resolveArticleRoute(article);

  const [isPrefetched, setIsPrefetched] = useState(false);
  const hoverTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Side Effect 1: Report invalid route telemetry on mount
  useEffect(() => {
    if (route.kind === "invalid") {
      reportNavigationError({
        articleId: article?.id,
        slug: article?.slug,
        url: article?.url,
        reason: route.reason || "Invalid article route",
        component: `ArticleLink[${section}]`,
      });
    }
  }, [route.kind, route.reason, article?.id, article?.slug, article?.url, section]);

  // Clean up hover timer on unmount
  useEffect(() => {
    return () => {
      if (hoverTimerRef.current) {
        clearTimeout(hoverTimerRef.current);
      }
    };
  }, []);

  // 150ms Intent-Debounced Hover Prefetching Handler
  const handleMouseEnter = useCallback(() => {
    if (route.kind !== "internal" || prefetchPriority || isPrefetched) return;

    if (hoverTimerRef.current) clearTimeout(hoverTimerRef.current);

    // 150ms delay filters out fast cursor sweeps across card grids
    hoverTimerRef.current = setTimeout(() => {
      router.prefetch(route.href);
      setIsPrefetched(true);
    }, 150);
  }, [route.kind, route.href, prefetchPriority, isPrefetched, router]);

  const handleMouseLeave = useCallback(() => {
    if (hoverTimerRef.current) {
      clearTimeout(hoverTimerRef.current);
      hoverTimerRef.current = null;
    }
  }, []);

  // Click Handler with Analytics Emission
  const handleClick = (e: React.MouseEvent) => {
    if (route.kind === "invalid") {
      e.preventDefault();
      e.stopPropagation();
      return;
    }

    trackArticleClick({
      articleId: article.id,
      slug: article.slug,
      sourceComponent: section,
      homepageSection: section,
      position,
    });

    if (onClick) {
      onClick(e);
    }

    // Programmatic fallback navigation when default is not prevented by custom click handlers
    if (!e.defaultPrevented && route.kind === "internal") {
      e.preventDefault();
      router.push(route.href);
    }
  };

  // Render Kind: Invalid (Disabled State UX)
  if (route.kind === "invalid") {
    return (
      <div
        ref={ref as React.Ref<HTMLDivElement>}
        className={`${className} cursor-not-allowed opacity-70 select-none`}
        style={style}
        aria-disabled="true"
        title="Article unavailable"
        role="button"
        tabIndex={-1}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            handleClick(e as any);
          }
        }}
        onClick={handleClick}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        data-testid="article-link-invalid"
      >
        {children}
      </div>
    );
  }

  // Render Kind: External Publisher Anchor
  if (route.kind === "external") {
    return (
      <a
        ref={ref as React.Ref<HTMLAnchorElement>}
        href={route.href}
        target={route.target || "_blank"}
        rel={route.rel || "noopener noreferrer"}
        className={className}
        style={style}
        onClick={handleClick}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        data-testid="article-link-external"
      >
        {children}
      </a>
    );
  }

  // Render Kind: Internal Next.js Link
  return (
    <Link
      ref={ref as React.Ref<HTMLAnchorElement>}
      href={route.href}
      prefetch={prefetchPriority || isPrefetched}
      className={className}
      style={style}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onClick={handleClick}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      data-testid="article-link-internal"
    >
      {children}
    </Link>
  );
});
