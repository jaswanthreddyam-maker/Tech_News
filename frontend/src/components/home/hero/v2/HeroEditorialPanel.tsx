"use client";

import React from "react";
import { m, AnimatePresence } from "framer-motion";
import { useHeroScene } from "./HeroSceneProvider";
import { ArticleLink } from "@/domains/article/ArticleLink";

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05,
      delayChildren: 0.05,
    },
  },
  exit: {
    opacity: 0,
    transition: { duration: 0.2 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: [0.25, 0.8, 0.25, 1] as [number, number, number, number] },
  },
};

export function HeroEditorialPanel() {
  const { activeArticle, activeIndex, arrivalFinished, interactionMode, setInteractionMode, onPrimaryAction } = useHeroScene();

  if (!activeArticle) {
    return <div className="h-64 flex items-center text-muted-foreground font-mono text-sm">Loading editorial state...</div>;
  }

  const isCardHovered = interactionMode === "hover";

  const handleAction = (e: React.MouseEvent) => {
    if (onPrimaryAction) {
      e.preventDefault();
      onPrimaryAction(activeArticle);
    }
  };

  return (
    <div
      className={`w-full max-w-[540px] flex flex-col justify-center text-foreground select-text transition-all duration-700 cubic-bezier(0.16, 1, 0.3, 1) ${
        arrivalFinished ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4 pointer-events-none"
      }`}
      onMouseEnter={() => setInteractionMode("reading")}
      onFocus={() => setInteractionMode("reading")}
      onMouseLeave={() => setInteractionMode("idle")}
      onBlur={() => setInteractionMode("idle")}
    >
      <AnimatePresence mode="wait">
        <m.div
          key={`${activeArticle.id}-${activeIndex}`}
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          exit="exit"
          className="flex flex-col gap-5"
        >
          {/* Staggered Element 1: Publisher & Category Emblem */}
          <m.div variants={itemVariants} className="flex items-center gap-3">
            <span className="inline-flex items-center px-3 py-1 text-xs font-mono font-extrabold uppercase tracking-wider rounded-md bg-white/[0.04] text-primary border border-white/[0.08] shadow-sm">
              {activeArticle.source || "EDITORIAL INTELLIGENCE"}
            </span>
            <span className="text-muted-foreground/60 text-xs font-mono">•</span>
            <span className="text-xs font-mono font-medium text-muted-foreground uppercase tracking-wide">
              {activeArticle.category || "TECH"}
            </span>
            {activeArticle.readTime && (
              <>
                <span className="text-muted-foreground/60 text-xs font-mono">•</span>
                <span className="text-xs font-mono font-semibold text-muted-foreground">
                  {activeArticle.readTime} MIN READ
                </span>
              </>
            )}
          </m.div>

          {/* Staggered Element 2: Architectural H1 Headline */}
          <m.h1
            variants={itemVariants}
            className="text-2xl sm:text-3xl lg:text-[34px] xl:text-[38px] font-bold tracking-tight leading-[1.12] text-foreground font-sans text-balance w-[90%] max-w-[360px] md:w-full md:max-w-none"
            style={{
              textShadow: "0 2px 24px rgba(0, 0, 0, 0.4)",
            }}
          >
            <ArticleLink
              article={activeArticle}
              onClick={handleAction}
              className="hover:text-primary transition-colors duration-300 outline-none focus-visible:ring-2 focus-visible:ring-primary rounded-sm"
            >
              {activeArticle.title}
            </ArticleLink>
          </m.h1>



          {/* Staggered Element 4: Interactive CTA with Signature Underline Micro-Animation */}
          <m.div variants={itemVariants} className="pt-2">
            <ArticleLink
              article={activeArticle}
              onClick={handleAction}
              className="group inline-flex items-center gap-2 text-sm sm:text-base font-semibold tracking-wide text-foreground hover:text-primary transition-colors duration-300 relative py-1 outline-none"
            >
              <span>Read Article</span>
              <span aria-hidden="true" className="transition-transform duration-300 group-hover:translate-x-1.5 text-primary">
                →
              </span>

              {/* Signature Hover Micro-Interaction Underline */}
              <span
                className={`absolute bottom-0 left-0 h-[2px] bg-primary transition-all duration-500 ease-out ${isCardHovered ? "w-full opacity-100" : "w-12 opacity-60 group-hover:w-full group-hover:opacity-100"
                  }`}
              />
            </ArticleLink>
          </m.div>
        </m.div>
      </AnimatePresence>
    </div>
  );
}
