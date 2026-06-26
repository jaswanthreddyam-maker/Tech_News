"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { m, useReducedMotion } from "framer-motion";
import { ArticleThumbnail } from "@/components/common/ArticleThumbnail";
import { FeaturedArticle } from "./types";
import { getImageVariants } from "./carousel.animations";
import { PREFETCH_CACHE_LIMIT } from "./carousel.constants";

interface HeroImageProps {
  article: FeaturedArticle;
  prevArticleImage?: string | null;
  nextArticleImage?: string | null;
  isPriority?: boolean;
  onPrimaryAction?: (article: FeaturedArticle, event: React.MouseEvent) => void;
}

// Client image prefetch cache with strict limit to prevent memory/resource leaks
const imageCache = new Set<string>();
const imageCacheQueue: string[] = [];

function prefetchImage(url: string | null) {
  if (!url || imageCache.has(url)) return;

  try {
    const img = new Image();
    img.src = url;
    imageCache.add(url);
    imageCacheQueue.push(url);

    if (imageCacheQueue.length > PREFETCH_CACHE_LIMIT) {
      const oldest = imageCacheQueue.shift();
      if (oldest) {
        imageCache.delete(oldest);
      }
    }
  } catch (err) {
    console.warn("Failed to prefetch image:", url, err);
  }
}

export function HeroImage({
  article,
  prevArticleImage,
  nextArticleImage,
  isPriority = false,
  onPrimaryAction,
}: HeroImageProps) {
  const shouldReduceMotion = !!useReducedMotion();
  const imageVariants = getImageVariants(shouldReduceMotion);

  useEffect(() => {
    if (prevArticleImage) {
      prefetchImage(prevArticleImage);
    }
    if (nextArticleImage) {
      prefetchImage(nextArticleImage);
    }
  }, [prevArticleImage, nextArticleImage]);

  // Construct a dummy article structure for ArticleThumbnail to maintain internal fallback compatibility
  const thumbnailArticle = {
    category: article.category,
    title: article.title,
    thumbnail_url: article.thumbnail,
    image_url: article.thumbnail,
  };

  return (
    <m.div
      variants={imageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      className="relative w-full h-full min-h-[300px] md:min-h-[350px] lg:min-h-[450px] overflow-hidden bg-neutral-900 group"
    >
      {/* Make the entire image clickable */}
      <Link 
        href={`/articles/${article.slug}`}
        onClick={(e) => onPrimaryAction?.(article, e)}
        draggable={false}
        className="absolute inset-0 z-20 cursor-pointer"
        aria-label={`Read ${article.title}`}
      >
        <span className="sr-only">Read {article.title}</span>
      </Link>

      <ArticleThumbnail
        article={thumbnailArticle}
        className="w-full h-full border-none transition-transform duration-700 ease-out group-hover:scale-105"
        imgClassName="object-cover transition-opacity duration-500 ease-in-out"
        sizes="(max-width: 768px) 100vw, (max-width: 1200px) 60vw, 40vw"
        priority={isPriority}
      />
      <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent pointer-events-none z-10" />
    </m.div>
  );
}

HeroImage.displayName = "HeroImage";
