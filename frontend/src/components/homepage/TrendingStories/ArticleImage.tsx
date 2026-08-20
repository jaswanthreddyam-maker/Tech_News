"use client";

import Image from "next/image";
import { useState } from "react";
import { MediaService } from "@/domains/article/media";
import { CategoryPlaceholder } from "@/components/common/media/CategoryPlaceholder";

interface ArticleImageProps {
  src?: string | null;
  alt: string;
  category?: string | null;
  className?: string;
  aspectRatio?: string;
}

/**
 * ArticleImage — Production Media Renderer for Article Cards
 * 
 * Enforces 1-to-1 article image mapping. Eliminates stock photo fallback arrays,
 * rendering CategoryPlaceholder when media is missing or marked as failed in MediaService.
 */
export function ArticleImage({
  src,
  alt,
  category,
  className = "",
  aspectRatio = "aspect-[4/3]",
}: ArticleImageProps) {
  const [hasError, setHasError] = useState(false);

  const resolvedSrc = (!hasError && src && !MediaService.isFailed(src)) 
    ? src 
    : MediaService.getCategoryFallbackImage(category, alt);

  const handleError = () => {
    if (src) {
      MediaService.markFailed(src);
    }
    setHasError(true);
  };

  return (
    <div className={`relative overflow-hidden bg-neutral-950 flex-none ${aspectRatio} ${className}`}>
      {resolvedSrc ? (
        <>
          <Image
            src={resolvedSrc}
            alt=""
            fill
            className="object-cover blur-xl scale-125 opacity-70 select-none pointer-events-none"
            aria-hidden="true"
            unoptimized
          />
          <Image
            src={resolvedSrc}
            alt={alt}
            fill
            sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
            className="object-cover object-center relative z-10 drop-shadow-md transition-transform duration-500 group-hover:scale-105"
            loading="lazy"
            unoptimized
            onError={handleError}
          />
        </>
      ) : (
        <CategoryPlaceholder category={category} className="absolute inset-0" />
      )}
    </div>
  );
}
