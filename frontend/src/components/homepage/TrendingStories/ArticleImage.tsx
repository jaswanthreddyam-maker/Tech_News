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

  const isFailed = src ? MediaService.isFailed(src) : false;
  const isInvalid = !src || hasError || isFailed;

  const handleError = () => {
    if (src) {
      MediaService.markFailed(src);
    }
    setHasError(true);
  };

  return (
    <div className={`relative overflow-hidden bg-muted flex-none ${aspectRatio} ${className}`}>
      {isInvalid || !src ? (
        <CategoryPlaceholder category={category} className="absolute inset-0" />
      ) : (
        <>
          <Image
            src={src}
            alt=""
            fill
            className="object-cover blur-xl scale-125 opacity-70 select-none pointer-events-none"
            aria-hidden="true"
            unoptimized
          />
          <Image
            src={src}
            alt={alt}
            fill
            sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
            className="object-contain object-center p-1.5 relative z-10 drop-shadow-md"
            loading="lazy"
            unoptimized
            onError={handleError}
          />
        </>
      )}
    </div>
  );
}
