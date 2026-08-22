"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from "react";
import {
  HeroSceneState,
  HeroSceneActions,
  HeroSceneContextType,
  HeroSceneProps,
  InteractionMode,
  PlaybackState,
} from "./types";

const HeroSceneContext = createContext<HeroSceneContextType | undefined>(undefined);

const PLAYBACK_CONFIG = {
  TOTAL_RING_CYCLE_MS: 90000,
  MIN_STEP_INTERVAL_MS: 8000,
  TRANSITION_DURATION_MS: 600,
};

import { MediaService } from "@/domains/article/media";

export function HeroSceneProvider({
  items: rawItems = [],
  editorPicks = [],
  latest = [],
  aiInsights = [],
  initialIndex = 0,
  isInView = true,
  onSlideChange,
  onPrimaryAction,
  onInsightClick,
  children,
}: React.PropsWithChildren<HeroSceneProps>) {
  const items = useMemo(() => rawItems.filter((a) => MediaService.hasGenuineThumbnail(a)), [rawItems]);
  const itemCount = items.length;
  const anglePerItem = useMemo(() => (itemCount > 0 ? 360 / itemCount : 0), [itemCount]);

  // Calculate dynamic radius from N cards so cards never overlap or intersect
  const [radius, setRadius] = useState<number>(850);

  useEffect(() => {
    const calculateRadius = () => {
      if (typeof window === "undefined" || itemCount === 0) return;
      const windowWidth = window.innerWidth;
      const cardWidth = windowWidth < 768 ? 247 : 304;
      const minRadius = windowWidth < 768 ? 500 : 760;
      if (itemCount <= 2) {
        setRadius(minRadius);
        return;
      }
      const angleInRadians = Math.PI / itemCount;
      const derivedRadius = Math.round((cardWidth * 0.85) / Math.tan(angleInRadians));
      setRadius(Math.max(minRadius, derivedRadius));
    };

    calculateRadius();
    window.addEventListener("resize", calculateRadius, { passive: true });
    return () => window.removeEventListener("resize", calculateRadius);
  }, [itemCount]);

  const [activeIndex, setActiveIndexState] = useState<number>(() => {
    if (itemCount === 0) return 0;
    return Math.min(Math.max(0, initialIndex), itemCount - 1);
  });

  const [rotation, setRotation] = useState<number>(() => -activeIndex * (itemCount > 0 ? 360 / itemCount : 0));
  const [interactionMode, setInteractionMode] = useState<InteractionMode>("idle");
  const [playbackState, setPlaybackState] = useState<PlaybackState>("playing");
  const [focusedCardId, setFocusedCardId] = useState<string | null>(null);
  const [arrivalFinished, setArrivalFinished] = useState<boolean>(false);

  const activeArticle = useMemo(() => (itemCount > 0 ? items.at(activeIndex) || null : null), [items, activeIndex, itemCount]);

  // Sync rotation cleanly when index changes directly
  const setActiveIndex = useCallback(
    (indexOrUpdater: number | ((prev: number) => number)) => {
      setActiveIndexState((prev) => {
        const nextIdx = typeof indexOrUpdater === "function" ? indexOrUpdater(prev) : indexOrUpdater;
        const validIdx = itemCount > 0 ? ((nextIdx % itemCount) + itemCount) % itemCount : 0;
        if (validIdx !== prev) {
          onSlideChange?.(validIdx);
          setRotation(-validIdx * anglePerItem);
        }
        return validIdx;
      });
    },
    [itemCount, anglePerItem, onSlideChange]
  );

  const nextSlide = useCallback(() => {
    if (itemCount === 0) return;
    setPlaybackState("transitioning");
    setRotation((prev) => prev - anglePerItem);
    setActiveIndex((prev) => (prev + 1) % itemCount);
    setTimeout(() => {
      setPlaybackState((current) => (current === "transitioning" ? "playing" : current));
    }, PLAYBACK_CONFIG.TRANSITION_DURATION_MS);
  }, [itemCount, anglePerItem, setActiveIndex]);

  const prevSlide = useCallback(() => {
    if (itemCount === 0) return;
    setPlaybackState("transitioning");
    setRotation((prev) => prev + anglePerItem);
    setActiveIndex((prev) => ((prev - 1 + itemCount) % itemCount));
    setTimeout(() => {
      setPlaybackState((current) => (current === "transitioning" ? "playing" : current));
    }, PLAYBACK_CONFIG.TRANSITION_DURATION_MS);
  }, [itemCount, anglePerItem, setActiveIndex]);

  // Autoplay loop: total ring cycle ms -> advances smoothly ONLY when user has entered section and arrival animation is finished
  useEffect(() => {
    if (
      itemCount <= 1 ||
      interactionMode !== "idle" ||
      playbackState !== "playing" ||
      !arrivalFinished ||
      !isInView
    ) {
      return;
    }

    const stepInterval = Math.max(
      PLAYBACK_CONFIG.MIN_STEP_INTERVAL_MS,
      Math.floor(PLAYBACK_CONFIG.TOTAL_RING_CYCLE_MS / itemCount)
    );
    const timer = setInterval(() => {
      nextSlide();
    }, stepInterval);

    return () => clearInterval(timer);
  }, [itemCount, interactionMode, playbackState, arrivalFinished, isInView, nextSlide]);

  // Pause playback automatically when interaction mode shifts away from idle
  useEffect(() => {
    if (interactionMode !== "idle") {
      setPlaybackState("paused");
    } else {
      setPlaybackState("playing");
    }
  }, [interactionMode]);

  const value = useMemo<HeroSceneContextType>(
    () => ({
      items,
      editorPicks,
      latest,
      aiInsights,
      activeIndex,
      activeArticle,
      rotation,
      interactionMode,
      playbackState,
      focusedCardId,
      arrivalFinished,
      itemCount,
      radius,
      anglePerItem,
      setActiveIndex,
      nextSlide,
      prevSlide,
      setInteractionMode,
      setPlaybackState,
      setFocusedCardId,
      setRotation,
      setArrivalFinished,
      onPrimaryAction,
      onInsightClick,
    }),
    [
      items,
      editorPicks,
      latest,
      aiInsights,
      activeIndex,
      activeArticle,
      rotation,
      interactionMode,
      playbackState,
      focusedCardId,
      arrivalFinished,
      itemCount,
      radius,
      anglePerItem,
      setActiveIndex,
      nextSlide,
      prevSlide,
      setInteractionMode,
      setPlaybackState,
      setFocusedCardId,
      setRotation,
      setArrivalFinished,
      onPrimaryAction,
      onInsightClick,
    ]
  );

  return <HeroSceneContext.Provider value={value}>{children}</HeroSceneContext.Provider>;
}

export function useHeroScene(): HeroSceneContextType {
  const context = useContext(HeroSceneContext);
  if (!context) {
    throw new Error("useHeroScene must be used within a HeroSceneProvider");
  }
  return context;
}
