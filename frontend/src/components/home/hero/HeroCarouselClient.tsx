"use client";

import React, { useState, useRef, useEffect } from "react";
import { m, AnimatePresence } from "framer-motion";
import { FeaturedArticle, HeroCarouselClientProps } from "./types";
import { useHeroCarousel } from "./useHeroCarousel";
import { HeroContent } from "./HeroContent";
import { HeroImage } from "./HeroImage";
import { HeroInsights } from "./HeroInsights";
import { HeroIndicators } from "./HeroIndicators";
import { HeroControls } from "./HeroControls";
import { useRouter } from "next/navigation";

export function HeroCarouselClient({
  items,
  editorPicks,
  latest,
  aiInsights,
  initialIndex = 0,
  onSlideChange,
  onPrimaryAction,
  onInsightClick,
}: HeroCarouselClientProps) {
  const router = useRouter();
  const itemCount = items.length;
  console.log("[HeroCarousel] Mounted with itemCount:", itemCount);

  const {
    activeIndex,
    goToNext,
    goToPrev,
    goToIndex,
    isPlaying,
    setIsDragging,
    setIsHovered,
    setIsFocused,
    viewRef,
    handleKeyDown,
  } = useHeroCarousel(itemCount, initialIndex);

  // Transition locking: prevent rapid clicks from overlapping slide animations
  const [isTransitioning, setIsTransitioning] = useState(false);
  
  // Prevent AnimatePresence from crashing Next.js 15 SSR streams
  const [isMounted, setIsMounted] = useState(false);
  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Track dragging details to prevent accidental clicks during swipes
  const dragStartRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const dragDistanceRef = useRef<number>(0);

  useEffect(() => {
    onSlideChange?.(activeIndex);
  }, [activeIndex, onSlideChange]);

  const handlePrev = () => {
    if (isTransitioning) return;
    setIsTransitioning(true);
    goToPrev();
    setTimeout(() => setIsTransitioning(false), 450);
  };

  const handleNext = () => {
    if (isTransitioning) return;
    setIsTransitioning(true);
    goToNext();
    setTimeout(() => setIsTransitioning(false), 450);
  };

  const handleDragStart = (event: any, info: any) => {
    dragStartRef.current = { x: info.point.x, y: info.point.y };
    dragDistanceRef.current = 0;
    setIsDragging(true);
  };

  const handleDrag = (event: any, info: any) => {
    const dx = info.point.x - dragStartRef.current.x;
    const dy = info.point.y - dragStartRef.current.y;
    dragDistanceRef.current = Math.sqrt(dx * dx + dy * dy);
  };

  const handleDragEnd = (event: any, info: any) => {
    setIsDragging(false);

    const windowWidth = typeof window !== "undefined" ? window.innerWidth : 1000;
    const threshold = Math.min(80, windowWidth * 0.08);

    const swipe = info.offset.x;
    if (swipe < -threshold) {
      handleNext();
    } else if (swipe > threshold) {
      handlePrev();
    }
  };

  const handlePrimaryActionIntercept = (article: FeaturedArticle, event: React.MouseEvent) => {
    if (dragDistanceRef.current > 5) {
      event.preventDefault();
      event.stopPropagation();
      return;
    }

    event.preventDefault();
    if (event.ctrlKey || event.metaKey) {
      window.open(`/articles/${article.slug}`, '_blank');
    } else {
      router.push(`/articles/${article.slug}`);
    }

    onPrimaryAction?.(article);
  };

  // --- Path 1: 0 articles ---
  if (itemCount === 0) {
    console.log("[RUNTIME TRACE] HeroCarouselClient path: 0 articles");
    return (
      <div className="border border-border rounded-xl p-8 bg-card text-center text-muted-foreground select-text">
        No articles available in the featured section at this time.
      </div>
    );
  }

  // --- Path 2: 1 article (Hide all controls and tabs) ---
  if (itemCount === 1) {
    console.log("[RUNTIME TRACE] HeroCarouselClient path: 1 article");
    const article = items[0];
    return (
      <div className="border border-border rounded-xl p-6 lg:p-8 bg-card overflow-hidden">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          <div className="lg:col-span-6 flex flex-col justify-center">
            <HeroContent article={article} onPrimaryAction={onPrimaryAction} />
          </div>
          <div className="lg:col-span-6 relative w-full h-[300px] lg:h-[450px]">
            <HeroImage article={article} isPriority={true} onPrimaryAction={onPrimaryAction} />
          </div>
        </div>
      </div>
    );
  }

  // --- Path 3: 2+ articles (Normal Carousel) ---
  console.log("[RUNTIME TRACE] HeroCarouselClient path: 2+ articles (Normal Carousel)");
  const activeArticle = items[activeIndex];

  const prevIndex = (activeIndex - 1 + itemCount) % itemCount;
  const nextIndex = (activeIndex + 1) % itemCount;
  const prevArticleImage = items[prevIndex]?.thumbnail;
  const nextArticleImage = items[nextIndex]?.thumbnail;

  return (
    /* eslint-disable jsx-a11y/no-noninteractive-element-interactions, jsx-a11y/no-noninteractive-tabindex */
    <div
      data-testid="hero-carousel-marker"
      ref={viewRef}
      tabIndex={0}
      onKeyDown={handleKeyDown}
      onFocus={() => setIsFocused(true)}
      onBlur={() => setIsFocused(false)}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className="relative border border-border rounded-xl p-6 lg:p-8 bg-card/45 focus-visible:ring-1 focus-visible:ring-ring focus-visible:ring-offset-2 outline-none group/carousel select-none"
      role="region"
      aria-roledescription="carousel"
      aria-label="Top Stories"
    >
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 relative">
        <HeroControls onPrev={handlePrev} onNext={handleNext} disabled={isTransitioning} />

        {isMounted ? (
          <m.div
            drag="x"
            dragConstraints={{ left: 0, right: 0 }}
            onDragStart={handleDragStart}
            onDrag={handleDrag}
            onDragEnd={handleDragEnd}
            className="lg:col-span-9 grid grid-cols-1 lg:grid-cols-9 gap-8 cursor-grab active:cursor-grabbing pointer-events-auto"
          >
            <div className="lg:col-span-4 flex flex-col justify-center select-text">
              <AnimatePresence mode="wait">
                <m.div
                  key={`${activeArticle.id}-${activeIndex}`}
                  initial="initial"
                  animate="animate"
                  exit="exit"
                  className="h-full flex flex-col justify-center"
                >
                  <HeroContent article={activeArticle} onPrimaryAction={handlePrimaryActionIntercept} />
                </m.div>
              </AnimatePresence>
            </div>
            <div className="lg:col-span-5 relative overflow-hidden select-none">
              <AnimatePresence mode="wait">
                <m.div
                  key={`${activeArticle.id}-${activeIndex}`}
                  initial="initial"
                  animate="animate"
                  exit="exit"
                  className="w-full h-full"
                >
                  <HeroImage
                    article={activeArticle}
                    prevArticleImage={prevArticleImage}
                    nextArticleImage={nextArticleImage}
                    isPriority={activeIndex === 0}
                    onPrimaryAction={handlePrimaryActionIntercept}
                  />
                </m.div>
              </AnimatePresence>
            </div>
          </m.div>
        ) : (
          <div className="lg:col-span-9 grid grid-cols-1 lg:grid-cols-9 gap-8">
            <div className="lg:col-span-4 flex flex-col justify-center select-text">
              <div className="h-full flex flex-col justify-center">
                <HeroContent article={activeArticle} onPrimaryAction={handlePrimaryActionIntercept} />
              </div>
            </div>
            <div className="lg:col-span-5 relative overflow-hidden select-none">
              <HeroImage
                key={`${activeArticle.id}-${activeIndex}`}
                article={activeArticle}
                prevArticleImage={prevArticleImage}
                nextArticleImage={nextArticleImage}
                isPriority={activeIndex === 0}
                onPrimaryAction={handlePrimaryActionIntercept}
              />
            </div>
          </div>
        )}

        <div className="lg:col-span-3">
          <HeroInsights
            editorPicks={editorPicks}
            latest={latest}
            aiInsights={aiInsights}
            onInsightClick={onInsightClick}
          />
        </div>
      </div>

      <HeroIndicators itemCount={itemCount} activeIndex={activeIndex} isPlaying={isPlaying} onIndicatorClick={goToIndex} />
    </div>
    /* eslint-enable jsx-a11y/no-noninteractive-element-interactions, jsx-a11y/no-noninteractive-tabindex */
  );
}

HeroCarouselClient.displayName = "HeroCarouselClient";
