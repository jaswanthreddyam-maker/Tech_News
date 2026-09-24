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
  POINTER_CUTOFF: 165,
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
    interactionMode,
    playbackState,
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
    setLocalArrivalFinished(true);
    setContextArrivalFinished(true);

    if (typeof window !== "undefined") {
      (window as any).__heroArrivalCompleted = true;
      window.dispatchEvent(new CustomEvent("hero-arrival-complete"));
    }

    // Double-rAF transition enablement eliminates browser CSS transition snaps
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

    let startTime: number | null = null;
    let lastFrameTimestamp: number | null = null;

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
      if (!lastFrameTimestamp) lastFrameTimestamp = timestamp;
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
        arrivalRafRef.current = requestAnimationFrame(animateArrival);
      } else {
        if (arrivalRef.current) arrivalRef.current.style.transform = "translateZ(0px) scale(1)";
        if (spinRef.current) spinRef.current.style.transform = "rotateY(0deg)";

        // rAF ANIMATION-DRIVEN SETTLE HANDOFF (Stable & smooth standstill)
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

  // Dedicated unmount teardown for rAF loops
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
      // If unmounted mid-animation (e.g. React StrictMode development cycle), reset status so remount restarts
      if (arrivalStatusRef.current === "animating" || arrivalStatusRef.current === "settling") {
        arrivalStatusRef.current = "idle";
      }
    };
  }, []);

  const hasItems = Boolean(items && items.length > 0);

  // Master Physical Machine Arrival Engine
  useEffect(() => {
    if (!hasItems) return;

    if (arrivalFinished || arrivalStatusRef.current === "completed") {
      completeArrival();
      return;
    }

    // If already animating or settling, do NOT interrupt or repeat
    if (arrivalStatusRef.current === "animating" || arrivalStatusRef.current === "settling") {
      return;
    }

    // Safety watchdog: guarantees the arrival finishes within 6.5s no matter what happens
    if (!safetyWatchdogTimerRef.current) {
      safetyWatchdogTimerRef.current = setTimeout(() => {
        if (arrivalStatusRef.current !== "completed") {
          completeArrival();
        }
      }, 6500);
    }

    // Check if WelcomeOverlay is actively playing right now
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
    // Only re-run if item presence shifts (empty -> populated), arrivalFinished updates, or engine handlers change.
    // Explicitly avoids re-running on item array instance changes during query refetches.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasItems, arrivalFinished, completeArrival, startArrival]);

  // Continuous Museum Exhibit Turntable Rotation Engine (Slow-Motion)
  const ambientRotationRef = useRef<number>(0);
  const smoothedRotationRef = useRef<number>(rotation);
  const lastActiveIndexRef = useRef<number>(activeIndex);
  const lastSyncedRotationRef = useRef<number>(rotation);

  // Sync when rotation changes externally (e.g. user clicks a card or next arrow)
  useEffect(() => {
    if (rotation !== lastSyncedRotationRef.current) {
      lastSyncedRotationRef.current = rotation;
      ambientRotationRef.current = 0;
    }
  }, [rotation]);

  useEffect(() => {
    if (!localArrivalFinished) return;

    let ambientRafId: number;
    let lastTime = performance.now();
    const SLOW_MOTION_DEG_PER_SEC = 3.0; // 3.0 deg/sec = slow, cinematic turntable rotation

    const animateAmbient = (now: number) => {
      const dt = Math.min(0.05, (now - lastTime) / 1000);
      lastTime = now;

      // Rotate continuously in slow motion when idle and playing
      if (!isDragging && interactionMode === "idle" && playbackState === "playing") {
        ambientRotationRef.current += SLOW_MOTION_DEG_PER_SEC * dt;
      }

      if (ringRef.current && !isArrivingRef.current) {
        const targetRotation = rotationRef.current + dragOffsetRef.current - ambientRotationRef.current;
        if (isDragging) {
          smoothedRotationRef.current = targetRotation;
        } else {
          // Zero-velocity dampened exponential spring lerp
          const lerpFactor = 1 - Math.exp(-8.0 * dt);
          smoothedRotationRef.current += (targetRotation - smoothedRotationRef.current) * lerpFactor;
        }

        const netAngle = smoothedRotationRef.current;
        ringRef.current.style.transform = `translateZ(-${radiusRef.current}px) rotateX(${RING_CONFIG.BASE_TILT}deg) rotateY(${netAngle}deg)`;

        // Update card depth opacities, pointer events, and z-index directly on DOM
        const count = itemCountRef.current;
        const perItem = anglePerItemRef.current;
        if (count > 0 && perItem > 0) {
          for (let i = 0; i < count; i++) {
            const cardEl = cardRefs.current[i];
            if (!cardEl) continue;

            const itemAngle = i * perItem;
            const currentNetAngle = normalizeAngle(itemAngle + netAngle);
            const shortestAngle = Math.min(currentNetAngle, 360 - currentNetAngle);

            // Smooth atmospheric depth falloff so cards remain exposed all around the 3D ring
            // 0° (front): 1.0 -> 90° (sides): ~0.80 -> 180° (opposite side): ~0.60
            const depthOpacity = Math.max(0.60, 1 - (shortestAngle / 180) * 0.40);

            cardEl.style.opacity = String(depthOpacity);
            cardEl.style.visibility = "visible";
            cardEl.style.pointerEvents = shortestAngle > 165 ? "none" : "auto";
            cardEl.style.zIndex = String(Math.round((180 - shortestAngle) * 10));
          }

          // Advance active card index as the ring turns (pass syncRotation = false to not jerk rotation)
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
  }, [localArrivalFinished, isDragging, interactionMode, playbackState, setActiveIndex]);

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

      // Absorb the drag offset directly into ambientRotationRef so the ring NEVER snaps on release!
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
      {/* System 1: Camera Arrival Stage (Driven directly by GPU compositor during flight) */}
      <div
        ref={arrivalRef}
        className="relative w-full h-full flex items-center justify-center"
        style={{
          transformStyle: "preserve-3d",
          transform: (arrivalFinished || localArrivalFinished)
            ? "translateZ(0px) scale(1)"
            : (arrivalStatusRef.current === "animating" || arrivalStatusRef.current === "settling")
            ? undefined
            : `translateZ(${ARRIVAL_CONFIG.START_Z}px) scale(${ARRIVAL_CONFIG.INITIAL_SCALE})`,
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
              const zIndex = Math.round((180 - shortestAngleFromFront) * 10);

              // Combined single Z/Y matrix offset using ACTIVE_CARD_CONFIG constants
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
