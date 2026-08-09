"use client";

import React from "react";
import { ChevronRight } from "lucide-react";
import { useHeroScene } from "./HeroSceneProvider";

export function HeroTransparentControls() {
  const { nextSlide, prevSlide, setInteractionMode, itemCount } = useHeroScene();

  if (itemCount <= 1) return null;

  return (
    <>


      <button
        type="button"
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setInteractionMode("keyboard");
          nextSlide();
        }}
        className="absolute right-0 lg:right-4 top-1/2 -translate-y-1/2 z-40 p-2 rounded-full bg-transparent hover:bg-card/30 backdrop-blur-none hover:backdrop-blur-sm text-foreground/50 hover:text-foreground transition-all duration-300 outline-none focus-visible:ring-2 focus-visible:ring-primary group"
        aria-label="Next story"
      >
        <ChevronRight className="w-8 h-8 md:w-10 md:h-10 opacity-70 group-hover:opacity-100 transition-opacity drop-shadow-md" strokeWidth={1.5} />
      </button>
    </>
  );
}
