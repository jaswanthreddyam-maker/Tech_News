"use client";

import { useEffect, useRef } from "react";

interface CardTiltOptions {
  maxTiltDeg?: number;
  maxTranslateZ?: number;
  scaleOnHover?: number;
  lerpFactor?: number;
}

/**
 * useCardTilt — Decoupled 3D Cursor-Tracking Tilt Engine
 * 
 * Operates natively within the parent scene camera matrix (NO local perspective override).
 * Uses Pointer Events (pointerenter, pointermove, pointerleave) for mouse/touch/pen support.
 * Runs rAF loop dynamically ONLY while actively hovered or settling.
 */
export function useCardTilt<T extends HTMLElement>({
  maxTiltDeg = 7,
  maxTranslateZ = 12,
  scaleOnHover = 1.015,
  lerpFactor = 0.06,
}: CardTiltOptions = {}) {
  const ref = useRef<T | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return;
    }

    let rafId: number | null = null;
    let isHovered = false;

    let targetTiltX = 0;
    let targetTiltY = 0;
    let targetScale = 1;
    let targetZ = 0;

    let currentTiltX = 0;
    let currentTiltY = 0;
    let currentScale = 1;
    let currentZ = 0;

    let lightXPercent = 50;
    let lightYPercent = 50;

    // Cache state to avoid unnecessary style writes (compare formatted strings)
    let lastTiltX = "";
    let lastTiltY = "";
    let lastScale = "";
    let lastZ = "";
    let lastLightX = -999;
    let lastLightY = -999;

    const startAnimationLoop = () => {
      if (rafId !== null) return;
      rafId = requestAnimationFrame(updateMotion);
    };

    const handlePointerEnter = () => {
      isHovered = true;
      targetScale = scaleOnHover;
      targetZ = maxTranslateZ;
      el.style.willChange = "transform";
      startAnimationLoop();
    };

    const handlePointerMove = (e: PointerEvent) => {
      if (!isHovered) return;
      const rect = el.getBoundingClientRect();
      if (!rect.width || !rect.height) return;

      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const normX = Math.max(-1, Math.min(1, (mouseX - rect.width / 2) / (rect.width / 2)));
      const normY = Math.max(-1, Math.min(1, (mouseY - rect.height / 2) / (rect.height / 2)));

      targetTiltX = -normY * maxTiltDeg;
      targetTiltY = normX * maxTiltDeg;

      lightXPercent = Math.round(((normX + 1) / 2) * 100);
      lightYPercent = Math.round(((normY + 1) / 2) * 100);

      startAnimationLoop();
    };

    const handlePointerLeave = () => {
      isHovered = false;
      targetTiltX = 0;
      targetTiltY = 0;
      targetScale = 1;
      targetZ = 0;
      lightXPercent = 50;
      lightYPercent = 50;
      startAnimationLoop();
    };

    const updateMotion = () => {
      currentTiltX += (targetTiltX - currentTiltX) * lerpFactor;
      currentTiltY += (targetTiltY - currentTiltY) * lerpFactor;
      currentScale += (targetScale - currentScale) * lerpFactor;
      currentZ += (targetZ - currentZ) * lerpFactor;

      const tiltXFixed = currentTiltX.toFixed(2);
      const tiltYFixed = currentTiltY.toFixed(2);
      const zFixed = currentZ.toFixed(1);
      const scaleFixed = currentScale.toFixed(3);

      if (lastTiltX !== tiltXFixed) {
        el.style.setProperty("--tilt-x", `${tiltXFixed}deg`);
        lastTiltX = tiltXFixed;
      }
      if (lastTiltY !== tiltYFixed) {
        el.style.setProperty("--tilt-y", `${tiltYFixed}deg`);
        lastTiltY = tiltYFixed;
      }
      if (lastZ !== zFixed) {
        el.style.setProperty("--tilt-z", `${zFixed}px`);
        lastZ = zFixed;
      }
      if (lastScale !== scaleFixed) {
        el.style.setProperty("--tilt-scale", scaleFixed);
        lastScale = scaleFixed;
      }
      if (lastLightX !== lightXPercent) {
        el.style.setProperty("--card-light-x", `${lightXPercent}%`);
        lastLightX = lightXPercent;
      }
      if (lastLightY !== lightYPercent) {
        el.style.setProperty("--card-light-y", `${lightYPercent}%`);
        lastLightY = lightYPercent;
      }

      // Check if settled to stop rAF loop and free GPU
      const isSettled =
        !isHovered &&
        Math.abs(targetTiltX - currentTiltX) < 0.01 &&
        Math.abs(targetTiltY - currentTiltY) < 0.01 &&
        Math.abs(targetScale - currentScale) < 0.001 &&
        Math.abs(targetZ - currentZ) < 0.05;

      if (isSettled) {
        el.style.willChange = "auto";
        rafId = null;
      } else {
        rafId = requestAnimationFrame(updateMotion);
      }
    };

    el.addEventListener("pointerenter", handlePointerEnter);
    el.addEventListener("pointermove", handlePointerMove);
    el.addEventListener("pointerleave", handlePointerLeave);

    return () => {
      if (rafId !== null) cancelAnimationFrame(rafId);
      el.removeEventListener("pointerenter", handlePointerEnter);
      el.removeEventListener("pointermove", handlePointerMove);
      el.removeEventListener("pointerleave", handlePointerLeave);
    };
  }, [maxTiltDeg, maxTranslateZ, scaleOnHover, lerpFactor]);

  return ref;
}
