"use client";

import React, { createContext, useContext, useEffect, useRef, useState } from "react";
import { useReducedMotion } from "framer-motion";

export type MotionLifecycleState = "Dormant" | "Entering" | "Settling" | "Interactive" | "Idle";

interface MotionDirectorContextType {
  lifecycleState: MotionLifecycleState;
  cameraMultiplier: number;
  isReducedMotion: boolean;
  ref: React.RefObject<HTMLDivElement | null>;
}

const MotionDirectorContext = createContext<MotionDirectorContextType>({
  lifecycleState: "Dormant",
  cameraMultiplier: 1.0,
  isReducedMotion: false,
  ref: { current: null },
});

export function useMotionDirector() {
  return useContext(MotionDirectorContext);
}

interface MotionDirectorProps {
  children: React.ReactNode;
  cameraMultiplier?: number;
  className?: string;
}

export function MotionDirector({ children, cameraMultiplier = 1.0, className = "" }: MotionDirectorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [lifecycleState, setLifecycleState] = useState<MotionLifecycleState>("Dormant");
  const isReducedMotion = useReducedMotion() ?? false;

  useEffect(() => {
    if (isReducedMotion) {
      setLifecycleState("Interactive");
      return;
    }

    const element = containerRef.current;
    if (!element) return;

    // Scroll Band Observer (Prewarm at 20%, Reveal at 35%, Interactive at 55%)
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const ratio = entry.intersectionRatio;
          if (entry.isIntersecting) {
            if (ratio >= 0.55) {
              setLifecycleState("Interactive");
            } else if (ratio >= 0.35) {
              setLifecycleState("Settling");
            } else if (ratio >= 0.2) {
              setLifecycleState("Entering");
            }
          }
        });
      },
      {
        threshold: [0, 0.2, 0.35, 0.55],
      }
    );

    observer.observe(element);
    return () => observer.disconnect();
  }, [isReducedMotion]);

  return (
    <MotionDirectorContext.Provider
      value={{
        lifecycleState,
        cameraMultiplier,
        isReducedMotion,
        ref: containerRef,
      }}
    >
      <div ref={containerRef} className={className}>
        {children}
      </div>
    </MotionDirectorContext.Provider>
  );
}
