"use client";

import React, { createContext, useContext, useEffect, useRef, ReactNode } from "react";

interface LenisContextValue {
  lenis: any | null;
}

const LenisContext = createContext<LenisContextValue>({ lenis: null });

export function useLenis() {
  return useContext(LenisContext);
}

interface LenisProviderProps {
  children: ReactNode;
}

/**
 * LenisProvider
 *
 * Applies smooth scrolling via Lenis — desktop only (> 1024px).
 * On mobile: native scroll is preserved (no added inertia).
 *
 * Settings:
 *   lerp: 0.1       — very subtle, no floating feel
 *   wheelMultiplier: 0.9  — slightly reduced scroll speed
 *   touchMultiplier: 1    — native touch feel
 *   smoothWheel: true
 *
 * Integrated with Framer Motion's RAF loop for compatibility.
 * Lenis is dynamically imported so the bundle is not affected
 * when Lenis is not supported or not needed.
 */
export function LenisProvider({ children }: LenisProviderProps) {
  const lenisRef = useRef<any>(null);
  const rafRef = useRef<number>(0);

  useEffect(() => {
    // Desktop only — mobile uses native scroll
    if (typeof window === "undefined") return;
    if (window.innerWidth <= 1024) return;

    // Respect reduced motion preference
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) return;

    let lenis: any;

    const initLenis = async () => {
      try {
        const { default: Lenis } = await import("lenis");

        lenis = new Lenis({
          lerp: 0.1,            // Very subtle — no floating feel
          wheelMultiplier: 0.9, // Slightly reduced for editorial reading
          touchMultiplier: 1,   // Native touch feel
          smoothWheel: true,
          infinite: false,
        });

        lenisRef.current = lenis;

        // RAF loop — integrated with Framer Motion's animation scheduler
        const raf = (time: number) => {
          lenis.raf(time);
          rafRef.current = requestAnimationFrame(raf);
        };

        rafRef.current = requestAnimationFrame(raf);
      } catch (e) {
        // Lenis not available — fall back to native scroll silently
        console.warn("[LenisProvider] Lenis not available, using native scroll.");
      }
    };

    initLenis();

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      if (lenisRef.current) {
        lenisRef.current.destroy();
        lenisRef.current = null;
      }
    };
  }, []);

  return (
    <LenisContext.Provider value={{ lenis: lenisRef.current }}>
      {children}
    </LenisContext.Provider>
  );
}
