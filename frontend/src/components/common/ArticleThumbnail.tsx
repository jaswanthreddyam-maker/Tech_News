"use client";

import Image from "next/image";
import { useState, useEffect } from "react";
import { thumbnailService, ThumbnailResolution } from "@/lib/thumbnails/thumbnailService";
import { CategoryPlaceholder } from "./placeholders/CategoryPlaceholder";

interface ArticleThumbnailProps {
  article: any;
  className?: string;
  imgClassName?: string;
  sizes?: string;
  alt?: string;
  priority?: boolean;
}

export function ArticleThumbnail({
  article,
  className = "",
  imgClassName = "object-cover",
  sizes = "(max-width: 768px) 100vw, 33vw",
  alt,
  priority = false
}: ArticleThumbnailProps) {
  // Always use a pure, server-compatible resolution for the initial state to prevent hydration mismatch
  const [resolution, setResolution] = useState<ThumbnailResolution>(() => {
    return thumbnailService.resolveThumbnail(article);
  });

  useEffect(() => {
    // Only after hydration (client-side), we can safely check localStorage
    setResolution(thumbnailService.resolveThumbnail(article));
  }, [article]);

  const handleError = () => {
    if (resolution.src) {
      thumbnailService.markAsFailed(resolution.src);
      setResolution(thumbnailService.resolveThumbnail(article));
    }
  };

  return (
    <div className={`relative overflow-hidden bg-neutral-900 ${className}`}>
      {resolution.isFallback || !resolution.src ? (
        <CategoryPlaceholder category={article?.category} className="absolute inset-0" />
      ) : (
        <Image
          src={resolution.src}
          alt={alt || article?.title || "Article thumbnail"}
          fill
          sizes={sizes}
          priority={priority}
          className={imgClassName}
          placeholder="blur"
          blurDataURL={resolution.blurDataURL}
          onError={handleError}
          unoptimized={true} // Bypasses next/image remotePatterns requirement for dynamic news sources
        />
      )}
    </div>
  );
}
