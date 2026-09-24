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

    // Cache state to avoid unnecessary style writes
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

      // Single direct transform write per frame (pure compositor path)
      // Avoids 6 individual CSS variable mutations that force CSSOM recalculation
      el.style.transform = `perspective(800px) rotateX(${currentTiltX.toFixed(2)}deg) rotateY(${currentTiltY.toFixed(2)}deg) translateZ(${currentZ.toFixed(1)}px) scale(${currentScale.toFixed(3)})`;

      // Update lighting position CSS vars only when they actually change
      const lightXRounded = Math.round(lightXPercent);
      const lightYRounded = Math.round(lightYPercent);
      if (lastLightX !== lightXRounded) {
        el.style.setProperty("--card-light-x", `${lightXRounded}%`);
        lastLightX = lightXRounded;
      }
      if (lastLightY !== lightYRounded) {
        el.style.setProperty("--card-light-y", `${lightYRounded}%`);
        lastLightY = lightYRounded;
      }

      // Check if settled to stop rAF loop and free GPU
      const isSettled =
        !isHovered &&
        Math.abs(targetTiltX - currentTiltX) < 0.01 &&
        Math.abs(targetTiltY - currentTiltY) < 0.01 &&
        Math.abs(targetScale - currentScale) < 0.001 &&
        Math.abs(targetZ - currentZ) < 0.05;

      if (isSettled) {
        // Clear transform and willChange to release GPU layer
        el.style.transform = "";
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
