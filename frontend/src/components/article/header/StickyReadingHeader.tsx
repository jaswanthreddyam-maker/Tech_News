"use client";

import React, { useState, useEffect } from "react";
import { m, AnimatePresence } from "framer-motion";
import { BookOpen, Sparkles, ArrowUp, Type } from "lucide-react";
import { getPresentationConfig } from "@/domains/article/presentation";

interface StickyReadingHeaderProps {
  title: string;
  documentType?: string | null;
  isMultiTopic?: boolean | null;
  readingTimeMin?: number;
  largeTextMode?: boolean;
  onToggleLargeText?: () => void;
}

export function StickyReadingHeader({
  title,
  documentType,
  isMultiTopic,
  readingTimeMin = 5,
  largeTextMode = false,
  onToggleLargeText,
}: StickyReadingHeaderProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [progress, setProgress] = useState(0);

  const presentation = getPresentationConfig(documentType, isMultiTopic);

  useEffect(() => {
    const handleScroll = () => {
      const scrollY = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;

      // Show header after scrolling past 300px
      setIsVisible(scrollY > 300);

      // Compute scroll reading progress percentage
      if (docHeight > 0) {
        const pct = Math.min(100, Math.max(0, Math.round((scrollY / docHeight) * 100)));
        setProgress(pct);
      }
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <AnimatePresence>
      {isVisible && (
        <m.header
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
          className="fixed top-0 left-0 right-0 z-50 bg-background/85 backdrop-blur-md border-b border-border/60 shadow-sm"
        >
          {/* Scroll Reading Progress Bar */}
          <div
            className="h-0.5 bg-primary transition-all duration-150 ease-out"
            style={{ width: `${progress}%` }}
          />

          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-12 flex items-center justify-between gap-4">
            {/* Title & Badge */}
            <div className="flex items-center gap-3 min-w-0">
              <button
                type="button"
                onClick={scrollToTop}
                title="Scroll to top"
                className="p-1 rounded-full text-muted-foreground/60 hover:text-foreground hover:bg-muted/40 transition-colors shrink-0"
              >
                <ArrowUp className="w-4 h-4" />
              </button>

              <h2 className="font-serif text-sm font-bold text-foreground line-clamp-1 truncate">
                {title}
              </h2>
            </div>

            {/* Reading Context & Controls */}
            <div className="flex items-center gap-4 shrink-0 font-mono text-xs text-muted-foreground">
              <span className="hidden sm:inline-flex items-center gap-1.5 font-bold">
                <BookOpen className="w-3.5 h-3.5 text-primary" />
                <span>{progress}% read</span>
              </span>

              {onToggleLargeText && (
                <button
                  type="button"
                  onClick={onToggleLargeText}
                  className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] border transition-colors ${
                    largeTextMode
                      ? "bg-primary text-primary-foreground border-primary font-bold"
                      : "border-white/10 text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <Type className="w-3 h-3" />
                  <span>Aa</span>
                </button>
              )}
            </div>
          </div>
        </m.header>
      )}
    </AnimatePresence>
  );
}
