"use client";

import React, { useRef, useState, useCallback, useEffect } from "react";
import { useHeroScene } from "./HeroSceneProvider";
import { HeroMediaCard } from "./HeroMediaCard";

/** Reusable Easing & Math Helpers */
const easeInCubic = (t: number) => t * t * t;
const easeInQuad = (t: number) => t * t;
const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3);
const easeOutQuart = (t: number) => 1 - Math.pow(1 - t, 4); // Zero-velocity deceleration curve
const easeInOutSin = (t: number) => Math.sin(t * Math.PI * 0.5);
const normalizeAngle = (angle: number) => ((angle % 360) + 360) % 360;

/** Physical Trajectory Milestones (Cinematic Acceleration Curve) */
const TRAJECTORY_STAGES = [
  { p: 0.35, z: -1600, ease: easeInCubic }, // 0% - 35%: Slow cinematic start out of deep space
  { p: 0.70, z: -500, ease: easeInQuad },  // 35% - 70%: Accelerating forward flight
  { p: 0.90, z: -30, ease: easeOutCubic },  // 70% - 90%: Rapid approach into view
  { p: 1.00, z: 0, ease: easeOutCubic },    // 90% - 100%: Crisp final touchdown
];

/** Physical Motion Parameters */
const ARRIVAL_CONFIG = {
  TOTAL_DURATION: 2500, // 2500ms trajectory (3.0s total animation time with 500ms settle)
  TOTAL_SPIN: -360, // 1 single full 360° rotation (slow, heavy, cinema-grade)
  START_Z: -2200, // Deep space start
  FINAL_Z: 0, // Rest position
  INITIAL_SCALE: 0.6, // Starts small in deep space
  MAX_SCALE: 2.3, // Expands outward to a massive size during flight
  FINAL_SCALE: 1.0, // Slowly contracts back to original size as animation finishes
  PEAK_SCALE_P: 0.60, // Reaches peak massive size at 60% of trajectory
};

/** Active Card Extraction Configuration */
const ACTIVE_CARD_CONFIG = {
  EXTRACTION_Z: 75, // Prominently extrudes active card 75px forward out of the 3D ring
  LIFT_Y: -14, // Lifts active card -14px
};

/** Master Centralized Ring & Interaction Configuration */
const RING_CONFIG = {
  DRAG_SENSITIVITY: 0.35,
  TRANSITION_MS: 450,
  POINTER_CUTOFF: 70,
  OPACITY_START: 110,
  MOBILE_HIDE: 125,
  BASE_TILT: -3,
  TILT_REBOUND: 0.2,
  SETTLE_DURATION_MS: 500,
};

/**
 * Hero3DRing — Production Mechanical Engine (Butter-Smooth 60fps/120fps)
 * 
 * CRITICAL ARCHITECTURAL INVARIANTS:
 * 1. 100% GPU COMPOSITOR DRIVEN: Never mutate non-transform properties (opacity, filter, width, height) inside rAF loops.
 *    Perform ONLY 2 transform writes per frame: `arrivalRef` (translateZ + scale) and `spinRef` (rotateY).
 * 2. SINGLE-RESPONSIBILITY 3D TRANSFORM STACK:
 *    - `containerRef` (PerspectiveRoot)  → Static perspective (1450px)
 *    - `arrivalRef` (ArrivalStage)       → translateZ + scale ONLY
 *    - `spinRef` (SpinStage)             → rotateY ONLY
 *    - `ringRef` (RingStage)             → Carousel ring rotation ONLY
 *    - `HeroMediaCard`                   → Local card extraction transforms ONLY
 * 3. DOUBLE-rAF TRANSITION ENABLING: `setIsTransitionEnabled` after 2 idle frames prevents CSS transition snaps.
 * 4. STALE-CLOSURE ISOLATION: `rotationRef`, `dragOffsetRef`, `radiusRef` eliminate stale React state captures in rAF loops.
 */
export function Hero3DRing() {
  const {
    items,
    activeIndex,
    rotation,
    radius,
    anglePerItem,
    itemCount,
    setInteractionMode,
    setActiveIndex,
    setRotation,
    arrivalFinished,
    setArrivalFinished: setContextArrivalFinished,
  } = useHeroScene();

  const [dragOffsetAngle, setDragOffsetAngle] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const dragStartXRef = useRef<number | null>(null);
  const startRotationRef = useRef<number>(0);

  // Single React state updates for arrival completion and double-rAF transition enabling
  const [localArrivalFinished, setLocalArrivalFinished] = useState(false);
  const [isTransitionEnabled, setIsTransitionEnabled] = useState(false);

  // Direct DOM Refs
  const containerRef = useRef<HTMLDivElement>(null);
  const arrivalRef = useRef<HTMLDivElement>(null);
  const spinRef = useRef<HTMLDivElement>(null);
  const ringRef = useRef<HTMLDivElement>(null);
  const shadowRef = useRef<HTMLDivElement>(null);

  // Isolated State Refs (Eliminates Stale Closures in rAF Loops)
  const radiusRef = useRef(radius);
  useEffect(() => {
    radiusRef.current = radius;
  }, [radius]);

  const rotationRef = useRef(rotation);
  useEffect(() => {
    rotationRef.current = rotation;
  }, [rotation]);

  const dragOffsetRef = useRef(dragOffsetAngle);
  useEffect(() => {
    dragOffsetRef.current = dragOffsetAngle;
  }, [dragOffsetAngle]);

  // Pure Ref Arrival Drag Lock Flag
  const isArrivingRef = useRef(true);

  // Master Physical Machine Arrival Engine
  useEffect(() => {
    if (!items || items.length === 0) return;
    if (!isArrivingRef.current || arrivalFinished) {
      if (arrivalRef.current) arrivalRef.current.style.transform = "translateZ(0px) scale(1)";
      if (spinRef.current) spinRef.current.style.transform = "rotateY(0deg)";
      return;
    }

    let startTime: number | null = null;
    let lastFrameTimestamp: number | null = null;
    let rafId: number;
    let settleRafId: number | null = null;

    const {
      TOTAL_DURATION,
      TOTAL_SPIN,
      START_Z,
      INITIAL_SCALE,
      MAX_SCALE,
      FINAL_SCALE,
      PEAK_SCALE_P,
    } = ARRIVAL_CONFIG;

    // Trigger shadow CSS transition to full state (runs on GPU via CSS, not per-frame JS)
    if (shadowRef.current) {
      shadowRef.current.style.transform = "scale(1, 1)";
      shadowRef.current.style.opacity = "0.85";
    }

    const animateArrival = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      if (!lastFrameTimestamp) lastFrameTimestamp = timestamp;
      const dt = Math.min(0.033, (timestamp - lastFrameTimestamp) / 1000);
      lastFrameTimestamp = timestamp;

      const elapsed = timestamp - startTime;
      const moveProgress = Math.min(1, Math.max(0, elapsed / TOTAL_DURATION));

      // 1. Single 360° Rotation (Slow, heavy, zero-velocity standstill at rest)
      const spinProgress = easeOutQuart(moveProgress);
      const spinAngle = TOTAL_SPIN * spinProgress;

      // 2. Growth to Massive Size & Slow Reduction to Original Size
      let currentScale: number;
      if (moveProgress <= PEAK_SCALE_P) {
        const growProgress = moveProgress / PEAK_SCALE_P;
        const ease = easeInQuad(growProgress);
        currentScale = INITIAL_SCALE + (MAX_SCALE - INITIAL_SCALE) * ease;
      } else {
        const shrinkProgress = (moveProgress - PEAK_SCALE_P) / (1 - PEAK_SCALE_P);
        const ease = easeOutCubic(shrinkProgress);
        currentScale = MAX_SCALE - (MAX_SCALE - FINAL_SCALE) * ease;
      }

      // 3. Trajectory Interpolation via TRAJECTORY_STAGES
      let currentZ = START_Z;
      let prevP = 0;
      let prevZ = START_Z;

      for (let i = 0; i < TRAJECTORY_STAGES.length; i++) {
        const stage = TRAJECTORY_STAGES[i];
        if (moveProgress <= stage.p) {
          const localProgress = (moveProgress - prevP) / (stage.p - prevP);
          const ease = stage.ease(localProgress);
          currentZ = prevZ + (stage.z - prevZ) * ease;
          break;
        }
        prevP = stage.p;
        prevZ = stage.z;
      }

      // ONLY 2 GPU COMPOSITOR WRITES PER FRAME (translateZ + scale + rotateY)
      if (arrivalRef.current) arrivalRef.current.style.transform = `translateZ(${currentZ}px) scale(${currentScale})`;
      if (spinRef.current) spinRef.current.style.transform = `rotateY(${spinAngle}deg)`;

      if (elapsed < TOTAL_DURATION) {
        rafId = requestAnimationFrame(animateArrival);
      } else {
        if (arrivalRef.current) arrivalRef.current.style.transform = "translateZ(0px) scale(1)";
        if (spinRef.current) spinRef.current.style.transform = "rotateY(0deg)";

        // rAF ANIMATION-DRIVEN SETTLE HANDOFF (Stable & smooth standstill)
        const settleStartTime = performance.now();
        const animateSettle = (now: number) => {
          const settleElapsed = now - settleStartTime;
          const p = Math.min(1, settleElapsed / RING_CONFIG.SETTLE_DURATION_MS);
          const netRotation = rotationRef.current + dragOffsetRef.current;

          if (ringRef.current) {
            ringRef.current.style.transform = `translateZ(-${radiusRef.current}px) rotateX(${RING_CONFIG.BASE_TILT}deg) rotateY(${netRotation}deg)`;
          }

          if (p < 1) {
            settleRafId = requestAnimationFrame(animateSettle);
          } else {
            // Handoff executes directly from animation completion
            isArrivingRef.current = false;
            setLocalArrivalFinished(true);
            setContextArrivalFinished(true);
            if (typeof window !== "undefined") {
              window.dispatchEvent(new CustomEvent("hero-arrival-complete"));
            }

            // Double-rAF transition enablement eliminates browser CSS transition snaps
            requestAnimationFrame(() => {
              requestAnimationFrame(() => {
                setIsTransitionEnabled(true);
              });
            });
          }
        };

        settleRafId = requestAnimationFrame(animateSettle);
      }
    };

    // Synchronize arrival start with WelcomeOverlay on desktop viewports (>= 768px)
    const isWelcomeOverlayActive =
      typeof window !== "undefined" &&
      !window.matchMedia("(max-width: 767px)").matches &&
      sessionStorage.getItem("welcome-played") !== "1";

    if (isWelcomeOverlayActive) {
      // Set initial state paused in deep space while Welcome Overlay plays
      if (arrivalRef.current) arrivalRef.current.style.transform = `translateZ(${START_Z}px) scale(${INITIAL_SCALE})`;
      if (spinRef.current) spinRef.current.style.transform = "rotateY(0deg)";

      let isStarted = false;
      const startArrival = () => {
        if (isStarted) return;
        isStarted = true;
        window.removeEventListener("welcome-overlay-complete", handleOverlayComplete);
        rafId = requestAnimationFrame(animateArrival);
      };

      const handleOverlayComplete = () => {
        startArrival();
      };

      window.addEventListener("welcome-overlay-complete", handleOverlayComplete);

      return () => {
        window.removeEventListener("welcome-overlay-complete", handleOverlayComplete);
        if (rafId) cancelAnimationFrame(rafId);
        if (settleRafId) cancelAnimationFrame(settleRafId);
      };
    } else {
      rafId = requestAnimationFrame(animateArrival);
      return () => {
        if (rafId) cancelAnimationFrame(rafId);
        if (settleRafId) cancelAnimationFrame(settleRafId);
      };
    }
  }, [items?.length]);

  // Persistent Ring Assembly Transform (Disabled during arrival sequence)
  useEffect(() => {
    if (!ringRef.current || isArrivingRef.current) return;
    const netRotation = rotation + dragOffsetAngle;
    ringRef.current.style.transform = `translateZ(-${radiusRef.current}px) rotateX(${RING_CONFIG.BASE_TILT}deg) rotateY(${netRotation}deg)`;
  }, [rotation, dragOffsetAngle]);

  const handlePointerDown = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (isArrivingRef.current) return;
      if (e.button !== 0 && e.pointerType === "mouse") return;
      dragStartXRef.current = e.clientX;
      startRotationRef.current = rotation;
      setIsDragging(true);
      setInteractionMode("drag");
      e.currentTarget.setPointerCapture(e.pointerId);
    },
    [rotation, setInteractionMode]
  );

  const handlePointerMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!isDragging || dragStartXRef.current === null) return;
      const dx = e.clientX - dragStartXRef.current;
      const degDelta = dx * RING_CONFIG.DRAG_SENSITIVITY;
      setDragOffsetAngle(degDelta);
    },
    [isDragging]
  );

  const handlePointerUp = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!isDragging) return;
      setIsDragging(false);
      if (e.currentTarget.hasPointerCapture(e.pointerId)) {
        e.currentTarget.releasePointerCapture(e.pointerId);
      }

      const totalRotation = startRotationRef.current + dragOffsetAngle;
      setDragOffsetAngle(0);

      if (itemCount > 0) {
        const normalizedAngle = -totalRotation / anglePerItem;
        let roundedIndex = Math.round(normalizedAngle) % itemCount;
        roundedIndex = (roundedIndex + itemCount) % itemCount;

        setActiveIndex(roundedIndex);
        setRotation(-roundedIndex * anglePerItem);
      }

      requestAnimationFrame(() => {
        setInteractionMode("idle");
      });
    },
    [isDragging, dragOffsetAngle, itemCount, anglePerItem, setActiveIndex, setRotation, setInteractionMode]
  );

  const sceneRotation = rotation + dragOffsetAngle;

  return (
    <div
      ref={containerRef}
      data-testid="hero-3d-ring-container"
      className="relative w-full h-full flex items-center justify-center cursor-grab active:cursor-grabbing select-none overflow-visible py-8"
      style={{
        perspective: "1450px",
        perspectiveOrigin: "50% 50%",
        transformStyle: "preserve-3d",
      }}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
      onPointerLeave={handlePointerUp}
    >
      {/* Stage Shadow (CSS-transitioned, not per-frame JS) */}
      <div
        ref={shadowRef}
        className="absolute -bottom-6 w-[304px] h-[36px] rounded-full bg-[radial-gradient(ellipse_at_center,rgba(0,0,0,0.95)_0%,transparent_75%)] pointer-events-none z-0 transform -translate-y-2"
        style={{
          transform: "scale(0.2, 0.5)",
          opacity: 0,
          transition: "transform 2.2s cubic-bezier(0.22, 0.61, 0.36, 1), opacity 2.2s cubic-bezier(0.22, 0.61, 0.36, 1)",
          willChange: "transform, opacity",
        }}
      />

      {/* System 1: Camera Arrival Stage (Initial frame 0 set in deep space at -2200px) */}
      <div
        ref={arrivalRef}
        className="relative w-full h-full flex items-center justify-center"
        style={{
          transformStyle: "preserve-3d",
          transform: "translateZ(-2200px)",
          willChange: "transform",
        }}
      >
        {/* System 2: Motor Spin Velocity Layer */}
        <div
          ref={spinRef}
          className="relative w-full h-full flex items-center justify-center"
          style={{
            transformStyle: "preserve-3d",
            transform: "rotateY(0deg)",
            willChange: "transform",
          }}
        >
          {/* Persistent Ring Assembly */}
          <div
            ref={ringRef}
            className="relative w-0 h-0 z-10"
            style={{
              transformStyle: "preserve-3d",
              transform: `translateZ(-${radius}px) rotateX(${RING_CONFIG.BASE_TILT}deg) rotateY(${sceneRotation}deg)`,
              transition: isDragging || !isTransitionEnabled ? "none" : `transform ${RING_CONFIG.TRANSITION_MS}ms cubic-bezier(0.22, 0.61, 0.36, 1)`,
              willChange: "transform",
            }}
          >
            {items.map((article, idx) => {
              const itemAngle = idx * anglePerItem;
              const isActive = idx === activeIndex;

              const currentNetAngle = normalizeAngle(itemAngle + sceneRotation);
              const shortestAngleFromFront = Math.min(currentNetAngle, 360 - currentNetAngle);

              const depthOpacity =
                shortestAngleFromFront > RING_CONFIG.OPACITY_START
                  ? Math.max(0.2, 1 - (shortestAngleFromFront - 90) * 0.008)
                  : 1;

              const cardPointerEvents: React.CSSProperties["pointerEvents"] =
                shortestAngleFromFront > RING_CONFIG.POINTER_CUTOFF ? "none" : "auto";
              const isHiddenOnMobile = shortestAngleFromFront > RING_CONFIG.MOBILE_HIDE;
              const zIndex = Math.round((180 - shortestAngleFromFront) * 10);

              // Combined single Z/Y matrix offset using ACTIVE_CARD_CONFIG constants
              const cardZ = radius + (isActive ? ACTIVE_CARD_CONFIG.EXTRACTION_Z : 0);
              const cardY = isActive ? ACTIVE_CARD_CONFIG.LIFT_Y : 0;

              return (
                <HeroMediaCard
                  key={article.id || idx}
                  article={article}
                  index={idx}
                  isActive={isActive}
                  arrivalFinished={arrivalFinished}
                  className={isHiddenOnMobile ? "hidden sm:block" : ""}
                  style={{
                    transform: `rotateY(${itemAngle}deg) translateZ(${cardZ}px) translateY(${cardY}px)`,
                    transformStyle: "preserve-3d",
                    opacity: depthOpacity,
                    pointerEvents: cardPointerEvents,
                    zIndex,
                  }}
                />
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
