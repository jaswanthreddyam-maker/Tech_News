"use client";

import React from "react";
import { BackendArticleDTO, CanonicalArticle, normalizeCanonicalArticle } from "@/domains/article";
import { getPresentationForArticle, PresentationConfig } from "@/domains/article/presentation";
import { ArticleLink } from "@/domains/article/ArticleLink";
import {
  CardHeader,
  CardMedia,
  CardTopics,
  CardMetadata,
  CardFooter,
} from "./primitives";

interface AdaptiveStoryCardProps {
  article: CanonicalArticle | BackendArticleDTO;
  presentation?: PresentationConfig;
  className?: string;
}

export function AdaptiveStoryCard({
  article: rawArticle,
  presentation: overridePresentation,
  className = "",
}: AdaptiveStoryCardProps) {
  // Normalize article if raw DTO passed
  const article: CanonicalArticle = "title" in rawArticle && typeof rawArticle.title === "string" && "readTime" in rawArticle
    ? (rawArticle as CanonicalArticle)
    : normalizeCanonicalArticle(rawArticle as BackendArticleDTO);

  // Obtain PresentationConfig from Document Presentation System (or override)
  const presentation = overridePresentation || getPresentationForArticle(article);

  const { badge, accent, cardVariant, metadata } = presentation;
  const topics = article.primaryTopics;

  return (
    <ArticleLink article={article} className={`group block h-full ${className}`}>
      <article className="flex flex-col justify-between h-full p-4 rounded-xl bg-card/60 hover:bg-card border border-border/60 hover:border-border transition-all duration-300 shadow-sm hover:shadow-md space-y-4">
        <div className="space-y-3">
          {/* Card Header (Badge & Category) */}
          <CardHeader badge={badge} category={article.category} />

          {/* Media Asset */}
          <CardMedia
            image={article.image}
            title={article.title}
            accent={accent}
          />

          {/* Special Variant: Collection Card Topics */}
          {cardVariant === "collection" && topics && topics.length > 0 && (
            <CardTopics topics={topics} maxDisplay={3} />
          )}

          {/* Title */}
          <h3 className="font-serif text-lg font-bold text-foreground group-hover:text-primary transition-colors leading-snug line-clamp-2">
            {article.title}
          </h3>

          {/* Summary / Description */}
          {article.summary && (
            <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed font-sans">
              {article.summary}
            </p>
          )}
        </div>

        {/* Bottom Section: Metadata & Footer */}
        <div className="space-y-3 pt-2">
          <CardMetadata
            publishedAt={article.publishedAt}
            readTime={article.readTime}
            flags={metadata}
            authorName={article.source}
          />

          <CardFooter sourceName={article.source} />
        </div>
      </article>
    </ArticleLink>
  );
}
