"use client";

import React, { useRef, useState, useCallback, useEffect } from "react";
import { useHeroScene } from "./HeroSceneProvider";
import { HeroMediaCard } from "./HeroMediaCard";

/** Reusable Easing & Math Helpers */
const easeInCubic = (t: number) => t * t * t;
const easeInQuad = (t: number) => t * t;
const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3);
const easeOutQuart = (t: number) => 1 - Math.pow(1 - t, 4); // Zero-velocity deceleration curve
const normalizeAngle = (angle: number) => ((angle % 360) + 360) % 360;

/**
 * Adaptive Performance Tier System
 * 
 * Probes actual GPU/CPU frame times on mount using a short rAF burst,
 * then classifies the device into a performance tier to set the optimal
 * target frame interval for the 3D ring animation loops.
 */
type PerformanceTier = "high" | "mid" | "low";

const PERF_TIER_CONFIG: Record<PerformanceTier, { frameIntervalMs: number; label: string }> = {
  high: { frameIntervalMs: 0, label: "Native refresh rate" },    // 0 = no throttling
  mid:  { frameIntervalMs: 33.3, label: "~30fps" },
  low:  { frameIntervalMs: 50, label: "~20fps" },
};

function useDevicePerformanceTier(): { tier: PerformanceTier; frameIntervalMs: number } {
  const resultRef = useRef<{ tier: PerformanceTier; frameIntervalMs: number }>({
    tier: "high",
    frameIntervalMs: 0,
  });
  const probeCompleteRef = useRef(false);

  useEffect(() => {
    if (probeCompleteRef.current) return;
    if (typeof window === "undefined") return;

    const PROBE_FRAMES = 12;
    const frameTimes: number[] = [];
    let prevTimestamp: number | null = null;
    let frameCount = 0;
    let rafId: number;

    const probeFrame = (timestamp: number) => {
      if (prevTimestamp !== null) {
        frameTimes.push(timestamp - prevTimestamp);
      }
      prevTimestamp = timestamp;
      frameCount++;

      if (frameCount < PROBE_FRAMES + 1) {
        rafId = requestAnimationFrame(probeFrame);
      } else {
        const sorted = [...frameTimes].sort((a, b) => a - b);
        const mid = Math.floor(sorted.length / 2);
        const medianMs = sorted.length % 2 === 0
          ? (sorted[mid - 1] + sorted[mid]) / 2
          : sorted[mid];

        let tier: PerformanceTier;
        if (medianMs <= 18) {
          tier = "high";
        } else if (medianMs <= 28) {
          tier = "mid";
        } else {
          tier = "low";
        }

        resultRef.current = {
          tier,
          frameIntervalMs: PERF_TIER_CONFIG[tier].frameIntervalMs,
        };
        probeCompleteRef.current = true;
      }
    };

    rafId = requestAnimationFrame(probeFrame);
    return () => cancelAnimationFrame(rafId);
  }, []);

  return resultRef.current;
}

/** Physical Trajectory Milestones (Cinematic Acceleration Curve) */
const TRAJECTORY_STAGES = [
  { p: 0.35, z: -1600, ease: easeInCubic }, // 0% - 35%: Slow cinematic start out of deep space
  { p: 0.70, z: -500, ease: easeInQuad },  // 35% - 70%: Accelerating forward flight
  { p: 0.90, z: -30, ease: easeOutCubic },  // 70% - 90%: Rapid approach into view
  { p: 1.00, z: 0, ease: easeOutCubic },    // 90% - 100%: Crisp final touchdown
];

/** Physical Motion Parameters (Optimized for smooth viewport containment) */
const ARRIVAL_CONFIG = {
  TOTAL_DURATION: 2500, // 2500ms trajectory
  TOTAL_SPIN: -360, // 1 single full 360° rotation (slow, heavy, cinema-grade)
  START_Z: -2200, // Deep space start
  FINAL_Z: 0, // Rest position
  INITIAL_SCALE: 0.6, // Starts small in deep space
  MAX_SCALE: 1.25, // Controlled majestic expansion without GPU fill-rate exhaustion
  FINAL_SCALE: 1.0, // Contracts back to original size
  PEAK_SCALE_P: 0.60,
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
  POINTER_CUTOFF: 165,
  BASE_TILT: -3,
  TILT_REBOUND: 0.2,
  SETTLE_DURATION_MS: 500,
};

export function Hero3DRing() {
  const { frameIntervalMs } = useDevicePerformanceTier();
  const {
    items,
    activeIndex,
    rotation,
    radius,
    anglePerItem,
    itemCount,
    interactionMode,
    playbackState,
    isInView = true,
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

  const [localArrivalFinished, setLocalArrivalFinished] = useState(false);
  const [isTransitionEnabled, setIsTransitionEnabled] = useState(false);

  // Direct DOM Refs
  const containerRef = useRef<HTMLDivElement>(null);
  const arrivalRef = useRef<HTMLDivElement>(null);
  const spinRef = useRef<HTMLDivElement>(null);
  const ringRef = useRef<HTMLDivElement>(null);

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

  const itemCountRef = useRef(itemCount);
  useEffect(() => {
    itemCountRef.current = itemCount;
  }, [itemCount]);

  const anglePerItemRef = useRef(anglePerItem);
  useEffect(() => {
    anglePerItemRef.current = anglePerItem;
  }, [anglePerItem]);

  const cardRefs = useRef<(HTMLElement | null)[]>([]);

  // Pure Ref Arrival Drag Lock Flag
  const isArrivingRef = useRef(true);
  const arrivalStatusRef = useRef<"idle" | "waiting_overlay" | "animating" | "settling" | "completed">("idle");
  const arrivalRafRef = useRef<number | null>(null);
  const settleRafRef = useRef<number | null>(null);
  const overlayFallbackTimerRef = useRef<NodeJS.Timeout | null>(null);
  const safetyWatchdogTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Carousel-Style Step-by-Step Card Advance Engine State
  const ambientRotationRef = useRef<number>(0);
  const smoothedRotationRef = useRef<number>(rotation);
  const lastActiveIndexRef = useRef<number>(activeIndex);
  const lastSyncedRotationRef = useRef<number>(rotation);

  // Step carousel state
  const stepBaseAngleRef = useRef<number>(0);
  const stepTargetAngleRef = useRef<number>(0);
  const stepStartTimeRef = useRef<number>(0);
  const stepPhaseRef = useRef<"dwell" | "stepping">("dwell");
  const dwellStartTimeRef = useRef<number>(0);
  const isPostArrivalInitialRef = useRef<boolean>(true);

  /** Carousel Step Configuration */
  const POST_ARRIVAL_DWELL_MS = 3000;
  const STEP_DWELL_MS = 3000;
  const STEP_TRANSITION_MS = 800;
  const easeInOutCubicStep = (t: number) => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

  // Synchronous and complete arrival finalization
  const completeArrival = useCallback(() => {
    if (arrivalStatusRef.current === "completed") return;
    arrivalStatusRef.current = "completed";
    isArrivingRef.current = false;

    if (arrivalRafRef.current) {
      cancelAnimationFrame(arrivalRafRef.current);
      arrivalRafRef.current = null;
    }
    if (settleRafRef.current) {
      cancelAnimationFrame(settleRafRef.current);
      settleRafRef.current = null;
    }
    if (overlayFallbackTimerRef.current) {
      clearTimeout(overlayFallbackTimerRef.current);
      overlayFallbackTimerRef.current = null;
    }
    if (safetyWatchdogTimerRef.current) {
      clearTimeout(safetyWatchdogTimerRef.current);
      safetyWatchdogTimerRef.current = null;
    }

    if (arrivalRef.current) arrivalRef.current.style.transform = "translateZ(0px) scale(1)";
    if (spinRef.current) spinRef.current.style.transform = "rotateY(0deg)";
    if (ringRef.current) {
      ringRef.current.style.transform = `translateZ(-${radiusRef.current}px) rotateX(${RING_CONFIG.BASE_TILT}deg) rotateY(0deg)`;
    }

    ambientRotationRef.current = 0;
    smoothedRotationRef.current = 0;

    dwellStartTimeRef.current = performance.now();
    stepPhaseRef.current = "dwell";
    isPostArrivalInitialRef.current = true;

    setLocalArrivalFinished(true);
    setContextArrivalFinished(true);

    if (typeof window !== "undefined") {
      (window as any).__heroArrivalCompleted = true;
      window.dispatchEvent(new CustomEvent("hero-arrival-complete"));
    }

    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        setIsTransitionEnabled(true);
      });
    });
  }, [setContextArrivalFinished]);

  // Master Trajectory Flight Launcher
  const startArrival = useCallback(() => {
    if (
      arrivalStatusRef.current === "animating" ||
      arrivalStatusRef.current === "settling" ||
      arrivalStatusRef.current === "completed"
    ) {
      return;
    }

    arrivalStatusRef.current = "animating";
    isArrivingRef.current = true;

    if (overlayFallbackTimerRef.current) {
      clearTimeout(overlayFallbackTimerRef.current);
      overlayFallbackTimerRef.current = null;
    }

    if (arrivalRef.current) arrivalRef.current.style.transform = `translateZ(${ARRIVAL_CONFIG.START_Z}px) scale(${ARRIVAL_CONFIG.INITIAL_SCALE})`;
    if (spinRef.current) spinRef.current.style.transform = "rotateY(0deg)";

    let startTime: number | null = null;

    const {
      TOTAL_DURATION,
      TOTAL_SPIN,
      START_Z,
      INITIAL_SCALE,
      MAX_SCALE,
      FINAL_SCALE,
      PEAK_SCALE_P,
    } = ARRIVAL_CONFIG;

    const animateArrival = (timestamp: number) => {
      if (arrivalStatusRef.current === "completed") return;

      if (!startTime) startTime = timestamp;
      const elapsed = timestamp - startTime;
      const moveProgress = Math.min(1, Math.max(0, elapsed / TOTAL_DURATION));

      // 1. Single 360° Rotation
      const spinProgress = easeOutQuart(moveProgress);
      const spinAngle = TOTAL_SPIN * spinProgress;

      // 2. Growth & Smooth settle
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

      // 3. Trajectory Interpolation
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

      if (arrivalRef.current) arrivalRef.current.style.transform = `translateZ(${currentZ}px) scale(${currentScale})`;
      if (spinRef.current) spinRef.current.style.transform = `rotateY(${spinAngle}deg)`;

      if (elapsed < TOTAL_DURATION) {
        arrivalRafRef.current = requestAnimationFrame(animateArrival);
      } else {
        if (arrivalRef.current) arrivalRef.current.style.transform = "translateZ(0px) scale(1)";
        if (spinRef.current) spinRef.current.style.transform = "rotateY(0deg)";

        arrivalStatusRef.current = "settling";
        const settleStartTime = performance.now();
        const animateSettle = (now: number) => {
          if (arrivalStatusRef.current === "completed") return;
          const settleElapsed = now - settleStartTime;
          const p = Math.min(1, settleElapsed / RING_CONFIG.SETTLE_DURATION_MS);
          const netRotation = rotationRef.current + dragOffsetRef.current;

          if (ringRef.current) {
            ringRef.current.style.transform = `translateZ(-${radiusRef.current}px) rotateX(${RING_CONFIG.BASE_TILT}deg) rotateY(${netRotation}deg)`;
          }

          if (p < 1) {
            settleRafRef.current = requestAnimationFrame(animateSettle);
          } else {
            completeArrival();
          }
        };

        settleRafRef.current = requestAnimationFrame(animateSettle);
      }
    };

    arrivalRafRef.current = requestAnimationFrame(animateArrival);
  }, [completeArrival]);

  useEffect(() => {
    return () => {
      if (arrivalRafRef.current) {
        cancelAnimationFrame(arrivalRafRef.current);
        arrivalRafRef.current = null;
      }
      if (settleRafRef.current) {
        cancelAnimationFrame(settleRafRef.current);
        settleRafRef.current = null;
      }
      if (overlayFallbackTimerRef.current) {
        clearTimeout(overlayFallbackTimerRef.current);
        overlayFallbackTimerRef.current = null;
      }
      if (safetyWatchdogTimerRef.current) {
        clearTimeout(safetyWatchdogTimerRef.current);
        safetyWatchdogTimerRef.current = null;
      }
      if (arrivalStatusRef.current === "animating" || arrivalStatusRef.current === "settling") {
        arrivalStatusRef.current = "idle";
      }
    };
  }, []);

  const hasItems = Boolean(items && items.length > 0);

  useEffect(() => {
    if (!hasItems) return;

    if (arrivalFinished || arrivalStatusRef.current === "completed") {
      completeArrival();
      return;
    }

    if (arrivalStatusRef.current === "animating" || arrivalStatusRef.current === "settling") {
      return;
    }

    if (!safetyWatchdogTimerRef.current) {
      safetyWatchdogTimerRef.current = setTimeout(() => {
        if (arrivalStatusRef.current !== "completed") {
          completeArrival();
        }
      }, 6500);
    }

    const isOverlayDispatched =
      typeof window !== "undefined" && Boolean((window as any).__welcomeOverlayDispatched);
    const isWelcomePlayed =
      typeof window !== "undefined" && sessionStorage.getItem("welcome-played") === "1";
    const isMobile =
      typeof window !== "undefined" && window.matchMedia("(max-width: 767px)").matches;

    const isWelcomeOverlayActive = !isOverlayDispatched && !isWelcomePlayed && !isMobile;

    if (isWelcomeOverlayActive) {
      arrivalStatusRef.current = "waiting_overlay";
      if (arrivalRef.current) {
        arrivalRef.current.style.transform = `translateZ(${ARRIVAL_CONFIG.START_Z}px) scale(${ARRIVAL_CONFIG.INITIAL_SCALE})`;
      }
      if (spinRef.current) {
        spinRef.current.style.transform = "rotateY(0deg)";
      }

      const handleOverlayComplete = () => {
        window.removeEventListener("welcome-overlay-complete", handleOverlayComplete);
        startArrival();
      };

      window.addEventListener("welcome-overlay-complete", handleOverlayComplete, { once: true });

      if (!overlayFallbackTimerRef.current) {
        overlayFallbackTimerRef.current = setTimeout(() => {
          handleOverlayComplete();
        }, 4500);
      }

      return () => {
        window.removeEventListener("welcome-overlay-complete", handleOverlayComplete);
      };
    } else {
      startArrival();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasItems, arrivalFinished, completeArrival, startArrival]);

  useEffect(() => {
    if (rotation !== lastSyncedRotationRef.current) {
      lastSyncedRotationRef.current = rotation;
      ambientRotationRef.current = 0;
      stepPhaseRef.current = "dwell";
      dwellStartTimeRef.current = performance.now();
      isPostArrivalInitialRef.current = false;
    }
  }, [rotation]);

  useEffect(() => {
    if (!localArrivalFinished) return;

    let ambientRafId: number;
    let lastTime = performance.now();
    let lastRenderTime = 0;

    if (!dwellStartTimeRef.current) {
      dwellStartTimeRef.current = performance.now();
    }
    stepPhaseRef.current = "dwell";

    const animateAmbient = (now: number) => {
      // Suspend rendering computations when section is out of view, saving 100% GPU/CPU for rest of page
      if (!isInView && !isDragging) {
        ambientRafId = requestAnimationFrame(animateAmbient);
        return;
      }

      const dt = Math.min(0.05, (now - lastTime) / 1000);
      lastTime = now;

      if (!isDragging && interactionMode === "idle" && playbackState === "playing") {
        const perItem = anglePerItemRef.current;

        if (stepPhaseRef.current === "dwell") {
          const currentDwellBudget = isPostArrivalInitialRef.current
            ? POST_ARRIVAL_DWELL_MS
            : STEP_DWELL_MS;

          if (now - dwellStartTimeRef.current >= currentDwellBudget && perItem > 0) {
            stepPhaseRef.current = "stepping";
            stepBaseAngleRef.current = ambientRotationRef.current;
            stepTargetAngleRef.current = ambientRotationRef.current + perItem;
            stepStartTimeRef.current = now;
            isPostArrivalInitialRef.current = false;
          }
        }

        if (stepPhaseRef.current === "stepping") {
          const stepElapsed = now - stepStartTimeRef.current;
          const stepProgress = Math.min(1, stepElapsed / STEP_TRANSITION_MS);
          const easedProgress = easeInOutCubicStep(stepProgress);

          ambientRotationRef.current =
            stepBaseAngleRef.current +
            (stepTargetAngleRef.current - stepBaseAngleRef.current) * easedProgress;

          if (stepProgress >= 1) {
            ambientRotationRef.current = stepTargetAngleRef.current;
            stepPhaseRef.current = "dwell";
            dwellStartTimeRef.current = now;
          }
        }
      } else if (isDragging) {
        dwellStartTimeRef.current = now;
        stepPhaseRef.current = "dwell";
        isPostArrivalInitialRef.current = false;
      }

      const isSteppingNow = stepPhaseRef.current === "stepping";
      const shouldRender = isDragging || isSteppingNow || frameIntervalMs === 0 || (now - lastRenderTime) >= frameIntervalMs;

      if (shouldRender && ringRef.current && !isArrivingRef.current) {
        lastRenderTime = now;

        const targetRotation = rotationRef.current + dragOffsetRef.current - ambientRotationRef.current;
        if (isDragging) {
          smoothedRotationRef.current = targetRotation;
        } else {
          const lerpFactor = 1 - Math.exp(-8.0 * dt);
          smoothedRotationRef.current += (targetRotation - smoothedRotationRef.current) * lerpFactor;
        }

        const netAngle = smoothedRotationRef.current;
        ringRef.current.style.transform = `translateZ(-${radiusRef.current}px) rotateX(${RING_CONFIG.BASE_TILT}deg) rotateY(${netAngle}deg)`;

        const count = itemCountRef.current;
        const perItem = anglePerItemRef.current;
        if (count > 0 && perItem > 0) {
          for (let i = 0; i < count; i++) {
            const cardEl = cardRefs.current[i];
            if (!cardEl) continue;

            const itemAngle = i * perItem;
            const currentNetAngle = normalizeAngle(itemAngle + netAngle);
            const shortestAngle = Math.min(currentNetAngle, 360 - currentNetAngle);

            const depthOpacity = Math.max(0.60, 1 - (shortestAngle / 180) * 0.40);

            cardEl.style.opacity = String(depthOpacity);
            cardEl.style.visibility = "visible";
            cardEl.style.pointerEvents = shortestAngle > 165 ? "none" : "auto";
          }

          const frontIndex = ((Math.round(normalizeAngle(-netAngle) / perItem) % count) + count) % count;
          if (frontIndex !== lastActiveIndexRef.current) {
            lastActiveIndexRef.current = frontIndex;
            setActiveIndex(frontIndex, false);
          }
        }
      }

      ambientRafId = requestAnimationFrame(animateAmbient);
    };

    ambientRafId = requestAnimationFrame(animateAmbient);
    return () => cancelAnimationFrame(ambientRafId);
  }, [localArrivalFinished, isDragging, interactionMode, playbackState, setActiveIndex, frameIntervalMs, isInView]);

  const handlePointerDown = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (isArrivingRef.current) return;
      if (e.button !== 0 && e.pointerType === "mouse") return;
      dragStartXRef.current = e.clientX;
      startRotationRef.current = rotation;
      setIsDragging(true);
      setInteractionMode("drag");
      if (e.pointerType === "mouse") {
        e.currentTarget.setPointerCapture(e.pointerId);
      }
    },
    [rotation, setInteractionMode]
  );

  const handlePointerMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!isDragging || dragStartXRef.current === null) return;
      const dx = e.clientX - dragStartXRef.current;
      if (Math.abs(dx) > 10 && e.pointerType === "touch" && !e.currentTarget.hasPointerCapture(e.pointerId)) {
        e.currentTarget.setPointerCapture(e.pointerId);
      }
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

      ambientRotationRef.current -= dragOffsetAngle;
      setDragOffsetAngle(0);
      dragOffsetRef.current = 0;

      requestAnimationFrame(() => {
        setInteractionMode("idle");
      });
    },
    [isDragging, dragOffsetAngle, setInteractionMode]
  );

  const sceneRotation = rotation + dragOffsetAngle;

  return (
    <div
      ref={containerRef}
      data-testid="hero-3d-ring-container"
      className="relative w-full h-full flex items-center justify-center cursor-grab active:cursor-grabbing select-none overflow-visible py-8 touch-pan-y"
      style={{
        perspective: "1450px",
        perspectiveOrigin: "50% 50%",
        transformStyle: "preserve-3d",
        touchAction: "pan-y",
      }}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
      onPointerLeave={handlePointerUp}
    >
      {/* System 1: Camera Arrival Stage (Driven directly by GPU compositor during flight) */}
      <div
        ref={arrivalRef}
        className="relative w-full h-full flex items-center justify-center"
        style={{
          transformStyle: "preserve-3d",
          transform: (arrivalFinished || localArrivalFinished)
            ? "translateZ(0px) scale(1)"
            : undefined,
          willChange: "transform",
        }}
      >
        {/* System 2: Motor Spin Velocity Layer */}
        <div
          ref={spinRef}
          className="relative w-full h-full flex items-center justify-center"
          style={{
            transformStyle: "preserve-3d",
            transform: (arrivalFinished || localArrivalFinished)
              ? "rotateY(0deg)"
              : undefined,
            willChange: "transform",
          }}
        >
          {/* Persistent Ring Assembly */}
          <div
            ref={ringRef}
            className="relative w-0 h-0 z-10"
            style={{
              transformStyle: "preserve-3d",
              transform: localArrivalFinished
                ? undefined
                : `translateZ(-${radius}px) rotateX(${RING_CONFIG.BASE_TILT}deg) rotateY(${sceneRotation}deg)`,
              transition: "none",
              willChange: "transform",
            }}
          >
            {items.map((article, idx) => {
              const itemAngle = idx * anglePerItem;
              const isActive = idx === activeIndex;

              const currentNetAngle = normalizeAngle(itemAngle + sceneRotation);
              const shortestAngleFromFront = Math.min(currentNetAngle, 360 - currentNetAngle);

              const depthOpacity = Math.max(0.60, 1 - (shortestAngleFromFront / 180) * 0.40);
              const cardPointerEvents: React.CSSProperties["pointerEvents"] =
                shortestAngleFromFront > 165 ? "none" : "auto";

              const cardZ = radius + (isActive ? ACTIVE_CARD_CONFIG.EXTRACTION_Z : 0);
              const cardY = isActive ? ACTIVE_CARD_CONFIG.LIFT_Y : 0;

              return (
                <HeroMediaCard
                  key={article.id || idx}
                  ref={(el) => {
                    cardRefs.current[idx] = el;
                  }}
                  article={article}
                  index={idx}
                  isActive={isActive}
                  arrivalFinished={arrivalFinished || localArrivalFinished}
                  className=""
                  style={{
                    transform: `rotateY(${itemAngle}deg) translateZ(${cardZ}px) translateY(${cardY}px)`,
                    transformStyle: "preserve-3d",
                    opacity: depthOpacity,
                    visibility: "visible",
                    pointerEvents: cardPointerEvents,
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
