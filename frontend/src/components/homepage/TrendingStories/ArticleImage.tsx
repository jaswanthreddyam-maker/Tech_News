"use client";

import Image from "next/image";
import { useState } from "react";
import { MediaService } from "@/domains/article/media";
import { CategoryPlaceholder } from "@/components/common/media/CategoryPlaceholder";

interface ArticleImageProps {
  src?: string | null;
  alt: string;
  category?: string | { name?: string } | null;
  seed?: string | number | null;
  className?: string;
  aspectRatio?: string;
}

/**
 * ArticleImage — Production Media Renderer for Article Cards
 * 
 * Enforces 1-to-1 article image mapping with high-entropy category photo fallback.
 */
export function ArticleImage({
  src,
  alt,
  category,
  seed,
  className = "",
  aspectRatio = "aspect-[4/3]",
}: ArticleImageProps) {
  const [hasError, setHasError] = useState(false);

  const resolvedSrc = (!hasError && src && !MediaService.isFailed(src)) 
    ? src 
    : null;

  const handleError = () => {
    if (src) {
      MediaService.markFailed(src);
    }
    setHasError(true);
  };

  return (
    <div className={`relative overflow-hidden bg-neutral-950 flex-none ${aspectRatio} ${className}`}>
      {resolvedSrc ? (
        <Image
          src={resolvedSrc}
          alt={alt}
          fill
          sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
          className="object-cover object-center relative z-10 transition-transform duration-300 group-hover:scale-105"
          loading="lazy"
          unoptimized
          onError={handleError}
        />
      ) : (
        <CategoryPlaceholder category={typeof category === "string" ? category : category?.name} className="absolute inset-0" />
      )}
    </div>
  );
}
