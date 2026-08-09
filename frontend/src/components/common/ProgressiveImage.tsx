/* eslint-disable @next/next/no-img-element, jsx-a11y/click-events-have-key-events, jsx-a11y/no-noninteractive-element-interactions */
"use client";

import React, { useState, useRef, useCallback } from "react";
import { cn } from "@/lib/utils";

interface ProgressiveImageProps {
  src: string;
  alt: string;
  className?: string;
  imgClassName?: string;
  dominantColor?: string; // hex or hsl — e.g. "#1a1a2e" or "hsl(220 40% 12%)"
  sizes?: string;
  onClick?: (e: React.MouseEvent<HTMLImageElement>) => void;
  priority?: boolean;
}

/**
 * ProgressiveImage
 *
 * Loads images with a dominant color placeholder → real image fade-in.
 * No blur filter on the real image (GPU-expensive on large images).
 * Blur is reserved for text animations only.
 *
 * The dominant color creates a smooth "Medium-style" load:
 * - Before load: a solid color matching the image's palette
 * - On load: opacity 0 → 1 over 400ms
 *
 * If no dominantColor is provided, falls back to muted/40 shimmer.
 */
export function ProgressiveImage({
  src,
  alt,
  className,
  imgClassName,
  dominantColor,
  sizes,
  onClick,
  priority = false,
}: ProgressiveImageProps) {
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);

  const handleLoad = useCallback(() => {
    setLoaded(true);
  }, []);

  const handleError = useCallback(() => {
    setError(true);
    setLoaded(true); // show the broken state
  }, []);

  // Check if already cached (browser cache means no load event fires)
  const handleRef = useCallback((node: HTMLImageElement | null) => {
    if (node) {
      if (node.complete && node.naturalWidth > 0) {
        setLoaded(true);
      }
    }
  }, []);

  return (
    <div
      className={cn("relative overflow-hidden", className)}
      style={{
        backgroundColor: dominantColor || undefined,
      }}
    >
      {/* Shimmer placeholder — shown while image loads */}
      {!loaded && (
        <div
          className="absolute inset-0 shimmer"
          style={dominantColor ? { background: dominantColor, opacity: 0.6 } : undefined}
          aria-hidden="true"
        />
      )}

      {/* The real image — fades in on load */}
      <img
        ref={(node) => {
          (imgRef as any).current = node;
          handleRef(node);
        }}
        src={src}
        alt={alt}
        sizes={sizes}
        loading={priority ? "eager" : "lazy"}
        decoding="async"
        onLoad={handleLoad}
        onError={handleError}
        onClick={onClick}
        className={cn(
          "w-full h-full object-cover transition-opacity duration-[400ms] ease-out",
          loaded ? "opacity-100" : "opacity-0",
          onClick && "cursor-zoom-in",
          imgClassName
        )}
        style={{
          // No blur filter — GPU expensive on large images
          willChange: loaded ? "auto" : "opacity",
        }}
      />
    </div>
  );
}
