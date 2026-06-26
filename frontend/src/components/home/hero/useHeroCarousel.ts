"use client";

import { useState, useEffect, useCallback } from "react";
import { useInView } from "react-intersection-observer";
import { AUTOPLAY_INTERVAL, LOOP } from "./carousel.constants";

export function useCarouselState(itemCount: number, initialIndex: number = 0) {
  const [activeIndex, setActiveIndex] = useState(initialIndex);

  const goToNext = useCallback(() => {
    setActiveIndex((prev) => {
      if (prev >= itemCount - 1) {
        return LOOP ? 0 : prev;
      }
      return prev + 1;
    });
  }, [itemCount]);

  const goToPrev = useCallback(() => {
    setActiveIndex((prev) => {
      if (prev <= 0) {
        return LOOP ? itemCount - 1 : prev;
      }
      return prev - 1;
    });
  }, [itemCount]);

  const goToIndex = useCallback((index: number) => {
    if (index >= 0 && index < itemCount) {
      setActiveIndex(index);
    }
  }, [itemCount]);

  return { activeIndex, goToNext, goToPrev, goToIndex };
}

export function useCarouselAutoplay(
  activeIndex: number,
  isPlaying: boolean,
  goToNext: () => void,
  interval: number = AUTOPLAY_INTERVAL
) {
  useEffect(() => {
    if (!isPlaying) return;

    const timer = setTimeout(() => {
      goToNext();
    }, interval);

    return () => clearTimeout(timer);
  }, [activeIndex, isPlaying, goToNext, interval]);
}

export function useCarouselKeyboard(
  goToNext: () => void,
  goToPrev: () => void,
  goToIndex: (index: number) => void,
  itemCount: number
) {
  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      if (event.key === "ArrowRight") {
        event.preventDefault();
        goToNext();
      } else if (event.key === "ArrowLeft") {
        event.preventDefault();
        goToPrev();
      } else if (event.key === "Home") {
        event.preventDefault();
        goToIndex(0);
      } else if (event.key === "End") {
        event.preventDefault();
        goToIndex(itemCount - 1);
      }
    },
    [goToNext, goToPrev, goToIndex, itemCount]
  );

  return { handleKeyDown };
}

export function useCarouselVisibility(onVisibilityChange: (visible: boolean) => void) {
  const { ref, inView } = useInView({
    threshold: 0.1,
  });

  const [documentVisible, setDocumentVisible] = useState(true);

  useEffect(() => {
    if (typeof document === "undefined") return;

    const handleVisibilityChange = () => {
      const visible = document.visibilityState === "visible";
      setDocumentVisible(visible);
      onVisibilityChange(inView && visible);
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    handleVisibilityChange(); // Initial check

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [inView, onVisibilityChange]);

  useEffect(() => {
    onVisibilityChange(inView && documentVisible);
  }, [inView, documentVisible, onVisibilityChange]);

  return { ref };
}

export function useHeroCarousel(itemCount: number, initialIndex: number = 0) {
  const { activeIndex, goToNext, goToPrev, goToIndex } = useCarouselState(itemCount, initialIndex);

  const [isHovered, setIsHovered] = useState(false);
  const [isFocused, setIsFocused] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [isViewVisible, setIsViewVisible] = useState(true);

  // Autoplay advances when page is visible and there are no active interactions
  const isPlaying = isViewVisible && !isHovered && !isFocused && !isDragging;

  const { ref: viewRef } = useCarouselVisibility(setIsViewVisible);

  useCarouselAutoplay(activeIndex, isPlaying, goToNext);

  const { handleKeyDown } = useCarouselKeyboard(goToNext, goToPrev, goToIndex, itemCount);

  return {
    activeIndex,
    goToNext,
    goToPrev,
    goToIndex,
    isPlaying,
    isDragging,
    setIsDragging,
    isHovered,
    setIsHovered,
    isFocused,
    setIsFocused,
    viewRef,
    handleKeyDown,
  };
}
