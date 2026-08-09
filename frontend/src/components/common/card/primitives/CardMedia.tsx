"use client";

import React from "react";
import Image from "next/image";
import { AccentColor } from "@/domains/article/presentation";

interface CardMediaProps {
  image?: string | null;
  title: string;
  accent?: AccentColor;
  aspectRatio?: string;
  className?: string;
}

const ACCENT_BORDER_MAP: Record<AccentColor, string> = {
  newsletter: "group-hover:border-white/30",
  roundup: "group-hover:border-white/30",
  opinion: "group-hover:border-white/30",
  review: "group-hover:border-white/30",
  live: "group-hover:border-emerald-500/40",
  breaking: "group-hover:border-rose-500/40",
  explainer: "group-hover:border-white/30",
  neutral: "group-hover:border-white/20",
};

export function CardMedia({
  image,
  title,
  accent = "neutral",
  aspectRatio = "aspect-video",
  className = "",
}: CardMediaProps) {
  const borderClass = ACCENT_BORDER_MAP[accent] || ACCENT_BORDER_MAP.neutral;

  return (
    <div
      className={`relative w-full ${aspectRatio} overflow-hidden rounded-lg bg-muted/40 border border-border/50 transition-colors duration-300 ${borderClass} ${className}`}
    >
      {image ? (
        <Image
          src={image}
          alt={title}
          fill
          sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
          className="object-cover transition-transform duration-500 ease-out group-hover:scale-105"
        />
      ) : (
        <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-muted/60 to-muted text-muted-foreground font-mono text-xs">
          Tech News Today
        </div>
      )}
    </div>
  );
}
