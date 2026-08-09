"use client";

import React, { useEffect, useState, useRef } from "react";

interface ReadingProgressProps {
  wordCount: number;
}

export function ReadingProgress({ wordCount }: ReadingProgressProps) {
  const [progress, setProgress] = useState(0);
  const [displayProgress, setDisplayProgress] = useState(0);
  const rafRef = useRef<number>(0);
  const mountedRef = useRef(false);
  const barRef = useRef<HTMLDivElement>(null);

  // Real-time scroll tracking via RAF — no CSS transition (avoids jitter)
  useEffect(() => {
    const updateProgress = () => {
      const scrollY = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const pct = docHeight > 0 ? Math.min(100, Math.max(0, (scrollY / docHeight) * 100)) : 0;
      setProgress(pct);
      // Direct DOM update for butter-smooth bar (bypass React re-render on every px)
      if (barRef.current) {
        barRef.current.style.width = `${pct}%`;
      }
    };

    const handleScroll = () => {
      rafRef.current = requestAnimationFrame(updateProgress);
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    updateProgress(); // initial
    return () => {
      window.removeEventListener("scroll", handleScroll);
      cancelAnimationFrame(rafRef.current);
    };
  }, []);

  // Mount animation: 0 → current scroll % over 600ms
  useEffect(() => {
    if (mountedRef.current) return;
    mountedRef.current = true;

    const start = performance.now();
    const duration = 600;
    const targetPct = progress;

    const animate = (now: number) => {
      const elapsed = now - start;
      const t = Math.min(1, elapsed / duration);
      // easeOut curve
      const easedT = 1 - Math.pow(1 - t, 3);
      const current = easedT * targetPct;
      setDisplayProgress(current);
      if (barRef.current) barRef.current.style.width = `${current}%`;
      if (t < 1) requestAnimationFrame(animate);
    };

    requestAnimationFrame(animate);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const READING_WPM = 220;
  const remainingMinutes = Math.max(0, Math.round((wordCount * (1 - progress / 100)) / READING_WPM));

  return (
    <>
      {/* Monochrome 2px progress line — top of screen */}
      <div className="fixed top-0 left-0 w-full h-[2px] bg-transparent z-[100] pointer-events-none">
        <div
          ref={barRef}
          className="h-full bg-foreground"
          style={{ width: "0%" }} // controlled by RAF, not state
        />
      </div>

      {/* Floating time remaining indicator */}
      <div
        className="fixed bottom-8 right-8 hidden xl:flex items-center gap-2 px-3 py-2 rounded-full bg-background/90 backdrop-blur border border-border text-xs font-mono font-bold text-muted-foreground shadow-lg z-[90] transition-opacity duration-300"
        style={{ opacity: progress > 1 && progress < 99 ? 1 : 0 }}
      >
        <span className="text-foreground">{Math.round(progress)}% read</span>
        <span className="text-border">|</span>
        <span className="text-foreground/60">
          {remainingMinutes > 0 ? `${remainingMinutes}m left` : "Finished"}
        </span>
      </div>
    </>
  );
}
