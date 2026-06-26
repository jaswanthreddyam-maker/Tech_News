"use client";

import React from "react";
import { m, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";
import { AUTOPLAY_INTERVAL } from "./carousel.constants";

interface HeroIndicatorsProps {
  itemCount: number;
  activeIndex: number;
  isPlaying: boolean;
  onIndicatorClick: (index: number) => void;
}

export function HeroIndicators({
  itemCount,
  activeIndex,
  isPlaying,
  onIndicatorClick,
}: HeroIndicatorsProps) {
  const shouldReduceMotion = !!useReducedMotion();

  if (itemCount <= 1) return null;

  return (
    <div className="absolute bottom-6 left-0 right-0 flex justify-center gap-3 z-30 pointer-events-none">
      {Array.from({ length: itemCount }).map((_, idx) => (
        <button
          key={idx}
          onClick={(e) => {
            e.stopPropagation();
            onIndicatorClick(idx);
          }}
          className={cn(
            "group relative h-1.5 rounded-full overflow-hidden transition-all duration-300 pointer-events-auto",
            "focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-4",
            activeIndex === idx ? "w-8 bg-primary/20" : "w-2 bg-border hover:bg-border/80"
          )}
          aria-label={`Go to slide ${idx + 1}`}
          aria-current={activeIndex === idx ? "true" : "false"}
        >
          {activeIndex === idx && isPlaying && (
            <m.div
              initial={{ width: "0%" }}
              animate={{ width: "100%" }}
              transition={{
                duration: AUTOPLAY_INTERVAL / 1000,
                ease: "linear",
              }}
              className="absolute top-0 left-0 bottom-0 bg-primary"
            />
          )}
          {activeIndex === idx && !isPlaying && (
            <div className="absolute top-0 left-0 bottom-0 w-full bg-primary" />
          )}
        </button>
      ))}
    </div>
  );
}

HeroIndicators.displayName = "HeroIndicators";
