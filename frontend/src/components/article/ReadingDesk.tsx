"use client";

import React, { useState } from "react";
import { StickyReadingHeader } from "./header/StickyReadingHeader";
import { CanonicalArticle } from "@/domains/article";
import { getPresentationForArticle } from "@/domains/article/presentation";

interface ReadingDeskProps {
  article: CanonicalArticle;
  children: React.ReactNode;
  className?: string;
}

export function ReadingDesk({ article, children, className = "" }: ReadingDeskProps) {
  const [largeTextMode, setLargeTextMode] = useState(false);
  const presentation = getPresentationForArticle(article);

  return (
    <div className={`relative min-h-screen bg-background text-foreground ${className}`}>
      {/* Sticky Progressive Header */}
      <StickyReadingHeader
        title={article.title}
        documentType={article.documentType}
        isMultiTopic={article.isMultiTopic}
        readingTimeMin={article.readTime || 5}
        largeTextMode={largeTextMode}
        onToggleLargeText={() => setLargeTextMode(!largeTextMode)}
      />

      {/* Main Physical Document Surface */}
      <main
        className={`
          max-w-4xl mx-auto transition-all duration-300
          ${largeTextMode ? "text-lg leading-relaxed" : "text-base leading-normal"}
        `}
      >
        {/* Quiet Editorial Context Bar */}
        <div className="flex flex-wrap items-center justify-between gap-4 py-3 px-4 mb-8 rounded-lg bg-white/[0.02] border border-white/10 text-xs font-mono text-muted-foreground/80">
          <div className="flex items-center gap-3">
            <span className="font-bold text-foreground">{article.source || "Tech News Today"}</span>
            <span>•</span>
            <span>{article.readTime || 5}m read</span>
          </div>

          <div className="flex items-center gap-2">
            <span className={`px-2 py-0.5 rounded-full border text-[10px] uppercase font-bold ${presentation.badge.className}`}>
              {presentation.badge.label}
            </span>
          </div>
        </div>

        {/* Reader Document Body */}
        <div className="prose-theme space-y-6">
          {children}
        </div>
      </main>
    </div>
  );
}
