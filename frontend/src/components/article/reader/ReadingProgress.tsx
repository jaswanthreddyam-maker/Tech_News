"use client";

import React, { useEffect, useState } from "react";

interface ReadingProgressProps {
  wordCount: number;
}

export function ReadingProgress({ wordCount }: ReadingProgressProps) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      const scrollY = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      if (docHeight > 0) {
        setProgress(Math.min(100, Math.max(0, (scrollY / docHeight) * 100)));
      }
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();

    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const READING_WPM = 220;
  const remainingMinutes = Math.max(0, Math.round((wordCount * (1 - progress / 100)) / READING_WPM));

  return (
    <>
      {/* Top Fixed Progress Bar */}
      <div className="fixed top-0 left-0 w-full h-1 bg-transparent z-[100] pointer-events-none">
        <div 
          className="h-full bg-primary transition-all duration-150 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Floating Percentage and Time Remaining Indicator */}
      <div className="fixed bottom-8 right-8 hidden xl:flex items-center gap-2 px-3 py-2 rounded-full bg-background/90 backdrop-blur border border-border text-xs font-mono font-bold text-muted-foreground shadow-lg z-[90] transition-opacity duration-300"
           style={{ opacity: progress > 1 && progress < 99 ? 1 : 0 }}>
        <span className="text-foreground">{Math.round(progress)}% read</span>
        <span className="text-border">|</span>
        <span className="text-primary">{remainingMinutes > 0 ? `${remainingMinutes}m left` : "Finished"}</span>
      </div>
    </>
  );
}
