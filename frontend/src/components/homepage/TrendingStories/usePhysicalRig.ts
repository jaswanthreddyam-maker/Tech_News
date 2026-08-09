"use client";

import { useEffect, useRef } from "react";
import { CAMERA_CONFIG } from "./constants";

/**
 * usePhysicalRig — Bulletproof Viewport-Wide 3D Camera Rig
 * 
 * 100% guaranteed continuous 3D matrix tilt (rotateX & rotateY) in response to cursor movement across the viewport.
 */
export function usePhysicalRig<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return;
    }

    let animationFrameId: number | null = null;
    let targetX = 0;
    let targetY = 0;
    let currentX = 0;
    let currentY = 0;

    const { LERP_FACTOR, MAX_TILT_DEG } = CAMERA_CONFIG;

    const startLoop = () => {
      if (animationFrameId === null) {
        animationFrameId = requestAnimationFrame(updateMotion);
      }
    };

    const handleMouseMove = (e: MouseEvent) => {
      const viewportWidth = window.innerWidth || 1200;
      const viewportHeight = window.innerHeight || 800;

      const normX = Math.max(-1, Math.min(1, (e.clientX - viewportWidth / 2) / (viewportWidth / 2 || 1)));
      const normY = Math.max(-1, Math.min(1, (e.clientY - viewportHeight / 2) / (viewportHeight / 2 || 1)));

      targetX = -normY * (MAX_TILT_DEG || 3.5);
      targetY = normX * (MAX_TILT_DEG || 3.5);

      const lightX = `${Math.round((normX * 0.5 + 0.5) * 100)}%`;
      const lightY = `${Math.round((normY * 0.5 + 0.5) * 100)}%`;
      el.style.setProperty("--wall-light-x", lightX);
      el.style.setProperty("--wall-light-y", lightY);

      startLoop();
    };

    const updateMotion = () => {
      const factor = LERP_FACTOR || 0.06;
      currentX += (targetX - currentX) * factor;
      currentY += (targetY - currentY) * factor;

      el.style.transform = `rotateX(${currentX.toFixed(3)}deg) rotateY(${currentY.toFixed(3)}deg)`;

      const isSettled =
        Math.abs(targetX - currentX) < 0.005 &&
        Math.abs(targetY - currentY) < 0.005;

      if (isSettled) {
        animationFrameId = null;
      } else {
        animationFrameId = requestAnimationFrame(updateMotion);
      }
    };

    window.addEventListener("mousemove", handleMouseMove, { passive: true });
    startLoop();

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      if (animationFrameId !== null) cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return ref;
}
