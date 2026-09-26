"use client";

import React, { useRef, useState, useEffect } from "react";
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
 * Preserves full 3D preserve-3d rendering context without flattening stacking contexts.
 */
export function HeroScene(props: HeroSceneProps) {
  const sectionRef = useRef<HTMLElement>(null);
  const [isInView, setIsInView] = useState(true);

  useEffect(() => {
    if (!sectionRef.current) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsInView(entry.isIntersecting && entry.intersectionRatio >= 0.05);
      },
      {
        threshold: [0, 0.05, 0.2, 0.5, 1.0],
      }
    );

    observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start start", "end start"],
  });
  const stageOpacity = useTransform(scrollYProgress, [0.9, 1], [1, 0.2]);

  return (
    <HeroSceneProvider {...props} isInView={isInView}>
      <m.section
        ref={sectionRef}
        style={{ opacity: stageOpacity }}
        data-testid="hero-scene-stage"
        aria-label="Featured AI Newsroom Stage"
        className="relative w-full overflow-visible bg-transparent min-h-[480px] sm:min-h-[520px] md:min-h-[640px] xl:min-h-[680px] pt-1 px-4 sm:px-6 lg:px-8 pb-12 sm:pb-16 md:pb-12 lg:pb-4 group/hero-stage select-none"
      >
        <HeroStageBackground />
        <HeroAtmosphere />

        {/* Editorial Panel & 3D Carousel Ring */}
        <div className="relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-2 sm:gap-4 lg:gap-8 xl:gap-12 items-center overflow-visible">
          {/* Left Editorial Panel */}
          <div className="lg:col-span-5 flex flex-col justify-start max-w-[540px] w-full mx-auto lg:mx-0 z-20 order-1 lg:order-1 -translate-y-2 sm:-translate-y-4 lg:-translate-y-[40px] pt-1 sm:pt-2 lg:pt-0">
            <HeroEditorialPanel />
          </div>

          {/* Right 3D Ring Assembly - Lifted upwards on mobile by up to 1 inch (~80px) */}
          <div className="lg:col-span-7 relative w-full flex flex-col items-center justify-center z-10 pointer-events-auto order-2 lg:order-2 overflow-visible h-[310px] sm:h-[370px] md:h-[440px] lg:h-[480px] -mt-8 sm:-mt-8 lg:mt-0 -translate-y-[80px] sm:-translate-y-[60px] md:-translate-y-[40px] lg:-translate-y-[30px]">
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
