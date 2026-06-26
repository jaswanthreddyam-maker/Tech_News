"use client";

import React from "react";
import { m } from "framer-motion";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { MotionScales } from "@/design-system/motion/tokens";

interface HeroControlsProps {
  onPrev: () => void;
  onNext: () => void;
  disabled?: boolean;
}

export function HeroControls({
  onPrev,
  onNext,
  disabled = false,
}: HeroControlsProps) {
  return (
    <div className="absolute top-1/2 -translate-y-1/2 left-0 right-0 flex justify-between px-4 pointer-events-none z-30">
      <m.button
        onClick={onPrev}
        disabled={disabled}
        whileHover={{ scale: MotionScales.hover }}
        whileTap={{ scale: MotionScales.tap }}
        className="p-2 rounded-full border border-border bg-card/85 text-foreground shadow hover:bg-accent hover:text-accent-foreground disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-2 pointer-events-auto transition-colors"
        aria-label="Previous story"
      >
        <ChevronLeft className="w-5 h-5" />
      </m.button>

      <m.button
        onClick={onNext}
        disabled={disabled}
        whileHover={{ scale: MotionScales.hover }}
        whileTap={{ scale: MotionScales.tap }}
        className="p-2 rounded-full border border-border bg-card/85 text-foreground shadow hover:bg-accent hover:text-accent-foreground disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-2 pointer-events-auto transition-colors"
        aria-label="Next story"
      >
        <ChevronRight className="w-5 h-5" />
      </m.button>
    </div>
  );
}

HeroControls.displayName = "HeroControls";
