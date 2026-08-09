"use client";

import React, { useRef } from "react";
import { m, useScroll, useTransform } from "framer-motion";
import { HeroSceneProps } from "./types";
import { HeroSceneProvider } from "./HeroSceneProvider";
import { HeroStageBackground } from "./HeroStageBackground";
import { HeroAtmosphere } from "./HeroAtmosphere";
import { Hero3DRing } from "./Hero3DRing";
import { HeroEditorialPanel } from "./HeroEditorialPanel";
import { HeroTransparentControls } from "./HeroTransparentControls";

/**
 * Hero v2: 3D Editorial Stage (Pitch OLED Black)
 */
export function HeroScene(props: HeroSceneProps) {
  const sectionRef = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start start", "end start"],
  });
  const opacity = useTransform(scrollYProgress, [0.5, 1], [1, 0]);

  // The early return has been removed to allow the 3D ring to mount immediately
  // with skeleton items passed from HeroCarousel while data is fetching.

  return (
    <HeroSceneProvider {...props}>
      <m.section
        ref={sectionRef}
        style={{ opacity }}
        data-testid="hero-scene-stage"
        aria-label="Featured AI Newsroom Stage"
        className="relative w-full overflow-visible bg-black min-h-[580px] md:min-h-[640px] xl:min-h-[680px] pt-1 px-4 sm:px-6 lg:px-8 pb-4 group/hero-stage select-none"
      >
        <HeroStageBackground />
        <HeroAtmosphere />

        {/* Editorial Panel & 3D Carousel Ring */}
        <div className="relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-8 xl:gap-12 items-center overflow-visible">
          {/* Left Panel */}
          <div className="lg:col-span-5 flex flex-col justify-start max-w-[540px] w-full mx-auto lg:mx-0 z-20 order-1 lg:order-1 lg:-translate-y-[40px] pt-4 lg:pt-0">
            <HeroEditorialPanel />
          </div>

          {/* Right 3D Ring */}
          <div className="lg:col-span-7 relative w-full flex flex-col items-center justify-center z-10 pointer-events-auto order-2 lg:order-2 overflow-visible h-[420px] sm:h-[460px] lg:h-[480px] -mt-24 sm:-mt-24 lg:mt-0 lg:-translate-y-[30px]">
            <div className="relative w-full h-full flex items-center justify-center overflow-visible">
              <Hero3DRing />
            </div>
            <HeroTransparentControls />
          </div>
        </div>
      </m.section>
    </HeroSceneProvider>
  );
}
