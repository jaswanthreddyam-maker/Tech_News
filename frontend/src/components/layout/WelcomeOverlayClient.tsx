"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { m, AnimatePresence } from "framer-motion";

/* ═══════════════════════════════════════════════════════════════════
 *  TYPES & CONFIGURATION
 * ═══════════════════════════════════════════════════════════════════ */

interface WelcomeOverlayClientProps {
  isMounted: boolean;
  hasPlayed: boolean | null;
  onComplete: () => void;
}

type Stage = 0 | 1 | 2 | 3; // 0 = idle/SSR, 1-3 = animation stages

/** Stage timeline — each entry is [enterDelay, holdDuration] in ms from animation start */
const TIMELINE: Record<1 | 2 | 3, number> = {
  1: 0,
  2: 1300,
  3: 2800,
};
const AUTO_REVEAL_AT = 5500;

/** Shared blur transition values */
const BLUR_ENTER = {
  opacity: 0,
  filter: "blur(16px)",
  scale: 0.97,
  y: 12,
};
const BLUR_VISIBLE = {
  opacity: 1,
  filter: "blur(0px)",
  scale: 1,
  y: 0,
};
const BLUR_EXIT = {
  opacity: 0,
  filter: "blur(16px)",
  scale: 0.97,
  y: 8,
};

/** Reduced-motion variants (simple fade) */
const FADE_ENTER = { opacity: 0 };
const FADE_VISIBLE = { opacity: 1 };
const FADE_EXIT = { opacity: 0 };

/** Premium easing curves */
const EASE_IN_OUT: [number, number, number, number] = [0.4, 0, 0.2, 1];
const EASE_OUT: [number, number, number, number] = [0, 0, 0.2, 1];
const PEEL_EASE: [number, number, number, number] = [0.76, 0, 0.24, 1];

/** Single word config */
const WORDS: { text: string; isBrand?: boolean }[] = [
  { text: "Welcome" },
  { text: "To" },
  { text: "Tech-News Today", isBrand: true },
];

/* ═══════════════════════════════════════════════════════════════════
 *  CSS KEYFRAMES — injected once into <head>
 * ═══════════════════════════════════════════════════════════════════ */

const CSS_KEYFRAMES = `
  @keyframes _wo-float {
    0%, 100% { transform: translateY(0) translateX(0) scale(1); opacity: 0.12; }
    50% { transform: translateY(-60px) translateX(15px) scale(1.3); opacity: 0.35; }
  }
  @keyframes _wo-flare {
    0% { transform: scaleX(0.9); opacity: 0.5; }
    100% { transform: scaleX(1.1); opacity: 0.75; }
  }
  @keyframes _wo-bounce {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(5px); }
  }
  @media (prefers-reduced-motion: reduce) {
    .wo-particle { animation: none !important; opacity: 0.12 !important; }
  }
`;

/* ═══════════════════════════════════════════════════════════════════
 *  PARTICLES — deterministic positions
 * ═══════════════════════════════════════════════════════════════════ */

const PARTICLES = [
  { top: "12%", left: "15%", s: 3, d: 0 },
  { top: "45%", left: "8%", s: 5, d: 2 },
  { top: "72%", left: "22%", s: 4, d: 1 },
  { top: "18%", left: "82%", s: 4, d: 3 },
  { top: "52%", left: "88%", s: 3, d: 0 },
  { top: "28%", left: "74%", s: 5, d: 5 },
  { top: "15%", left: "48%", s: 3, d: 3.5 },
  { top: "64%", left: "42%", s: 4, d: 1.5 },
  { top: "38%", left: "32%", s: 3, d: 4.5 },
];

/* ═══════════════════════════════════════════════════════════════════
 *  COMPONENT
 * ═══════════════════════════════════════════════════════════════════ */

export default function WelcomeOverlayClient({
  isMounted,
  hasPlayed,
  onComplete,
}: WelcomeOverlayClientProps) {
  const [stage, setStage] = useState<Stage>(0);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [isSkipping, setIsSkipping] = useState(false);
  const [skipTriggered, setSkipTriggered] = useState(false);
  const [isVisible, setIsVisible] = useState(true);
  const started = useRef(false);
  const completed = useRef(false);
  const overlayRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<Stage>(0);

  useEffect(() => {
    stageRef.current = stage;
  }, [stage]);

  // Detect prefers-reduced-motion
  useEffect(() => {
    const mql = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(mql.matches);
    const handler = (e: MediaQueryListEvent) => { setReducedMotion(e.matches); };
    mql.addEventListener("change", handler);
    return () => { mql.removeEventListener("change", handler); };
  }, []);

  // Inject keyframes
  useEffect(() => {
    const el = document.createElement("style");
    el.textContent = CSS_KEYFRAMES;
    document.head.appendChild(el);
    return () => { document.head.removeChild(el); };
  }, []);

  // Lock scroll during animation
  useEffect(() => {
    if (stage > 0 && !completed.current) {
      document.body.style.overflow = "hidden";
      window.scrollTo(0, 0);
    }
    return () => { document.body.style.overflow = ""; };
  }, [stage]);

  // Focus the overlay on mount for accessibility
  useEffect(() => {
    if (isMounted && hasPlayed === false && overlayRef.current) {
      overlayRef.current.focus();
    }
  }, [isMounted, hasPlayed]);

  const doComplete = useCallback(() => {
    if (completed.current) return;
    completed.current = true;
    document.body.style.overflow = "";
    setIsVisible(false);
  }, []);

  // State machine — deterministic single-timeline
  useEffect(() => {
    if (!isMounted || hasPlayed === true) return;
    if (started.current) return;
    started.current = true;

    // If reduced motion, skip straight to reveal after brief pause
    if (reducedMotion) {
      setStage(3);
      const t = setTimeout(doComplete, 1500);
      return () => { clearTimeout(t); };
    }

    const timers: ReturnType<typeof setTimeout>[] = [];
    for (const [key, delay] of Object.entries(TIMELINE)) {
      timers.push(setTimeout(() => { setStage(Number(key) as Stage); }, delay));
    }
    timers.push(setTimeout(doComplete, AUTO_REVEAL_AT));

    return () => { timers.forEach(clearTimeout); };
  }, [isMounted, hasPlayed, reducedMotion, doComplete]);

  // Skip handler
  const handleSkip = useCallback((e?: Event) => {
    if (completed.current) return;

    if (e && e.type === "keydown") {
      const keyEvent = e as KeyboardEvent;
      if (keyEvent.key === " " || keyEvent.key === "Enter") {
        keyEvent.preventDefault();
      }
    }

    // Skip with fade-out (200-300ms) only if interacting during the animation
    const shouldFade = stageRef.current < 3;
    setIsSkipping(shouldFade);
    setSkipTriggered(true);
  }, []);

  useEffect(() => {
    if (skipTriggered) {
      doComplete();
    }
  }, [skipTriggered, doComplete]);

  // Listen to skip interactions globally
  useEffect(() => {
    if (!isMounted || hasPlayed === true || completed.current) return;

    const handleGlobalInteraction = (e: Event) => {
      // Only left click triggers skip
      if (e.type === "mousedown" || e.type === "pointerdown") {
        const mouseEvent = e as MouseEvent;
        if (mouseEvent.button !== 0) return;
      }
      handleSkip(e);
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " " || e.key === "Escape") {
        handleSkip(e);
      }
    };

    window.addEventListener("mousedown", handleGlobalInteraction, { capture: true });
    window.addEventListener("touchstart", handleGlobalInteraction, { capture: true, passive: true });
    window.addEventListener("keydown", handleKeyDown, { capture: true });

    return () => {
      window.removeEventListener("mousedown", handleGlobalInteraction, { capture: true });
      window.removeEventListener("touchstart", handleGlobalInteraction, { capture: true });
      window.removeEventListener("keydown", handleKeyDown, { capture: true });
    };
  }, [isMounted, hasPlayed, handleSkip]);

  const handleClick = () => {
    if (stage === 3) doComplete();
  };

  /* ─── Animation variants ─── */
  const enterAnim = reducedMotion ? FADE_ENTER : BLUR_ENTER;
  const visibleAnim = reducedMotion ? FADE_VISIBLE : BLUR_VISIBLE;
  const exitAnim = reducedMotion ? FADE_EXIT : BLUR_EXIT;
  const wordDuration = reducedMotion ? 0.3 : 0.5;

  /* ─── SSR / pre-mount: render static Step 1 frame ─── */
  const isSSR = !isMounted || hasPlayed === null;
  const activeStage: Stage = isSSR ? 1 : stage === 0 ? 1 : stage;

  return (
    <AnimatePresence onExitComplete={onComplete}>
      {isVisible && (
        <m.div
          ref={overlayRef}
          key="welcome-overlay"
          initial={{ y: 0, opacity: 1 }}
          exit={isSkipping ? { opacity: 0 } : { y: "-100%" }}
          transition={{
            duration: isSkipping ? 0.25 : 1.0,
            ease: isSkipping ? "easeOut" : PEEL_EASE,
          }}
          onClick={handleClick}
          tabIndex={-1}
          role="dialog"
          aria-modal="true"
          aria-label="Welcome to Tech News Today. Press Enter, Space, Escape, or click anywhere to skip the welcome animation and enter the homepage."
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 99999,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            backgroundColor: "var(--background)",
            color: "var(--foreground)",
            overflow: "hidden",
            fontFamily: "Georgia, 'Times New Roman', serif",
            userSelect: "none",
            cursor: activeStage === 3 ? "pointer" : "default",
            willChange: "transform, opacity",
          }}
        >
      {/* ─── Ambient Particles ─── */}
      <div style={{ position: "absolute", inset: 0, overflow: "hidden", pointerEvents: "none" }}>
        {PARTICLES.map((p, i) => (
          <div
            key={i}
            className="wo-particle"
            style={{
              position: "absolute",
              top: p.top,
              left: p.left,
              width: `${p.s}px`,
              height: `${p.s}px`,
              backgroundColor: "var(--muted)",
              borderRadius: "50%",
              opacity: 0.12,
              filter: "blur(1px)",
              animation: `_wo-float ${10 + i * 0.7}s ease-in-out ${p.d}s infinite`,
              willChange: "transform, opacity",
            }}
          />
        ))}
      </div>

      {/* ─── Center Stage: Word Display ─── */}
      <div
        style={{
          position: "relative",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "140px",
          width: "100%",
        }}
      >
        <AnimatePresence mode="wait">
          {WORDS.map((word, i) => {
            const wordStage = (i + 1) as Stage;
            if (activeStage !== wordStage) return null;

            return (
              <m.div
                key={`word-${wordStage}`}
                initial={isSSR ? { opacity: 1 } : enterAnim}
                animate={visibleAnim}
                exit={exitAnim}
                transition={{
                  duration: wordDuration,
                  ease: EASE_IN_OUT,
                }}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  willChange: "transform, opacity, filter",
                }}
              >
                <h1
                  style={{
                    fontSize: word.isBrand
                      ? "clamp(3rem, 7.5vw, 5rem)"
                      : "clamp(2.5rem, 6vw, 4.2rem)",
                    fontWeight: word.isBrand ? 700 : 500,
                    letterSpacing: word.isBrand ? "-0.02em" : "0.02em",
                    margin: 0,
                    color: "var(--foreground)",
                    textShadow: "0 0 40px color-mix(in srgb, var(--accent) 20%, transparent)",
                    lineHeight: 1.1,
                  }}
                >
                  {word.text}
                </h1>

                {/* Subtle accent glow line — visible on stages 1, 3 */}
                {(wordStage === 1 || wordStage === 3) && (
                  <m.div
                    initial={{ opacity: 0, scaleX: 0.5 }}
                    animate={{ opacity: 0.6, scaleX: 1 }}
                    transition={{ duration: 1.2, ease: EASE_OUT, delay: 0.3 }}
                    style={{
                      marginTop: "20px",
                      width: "180px",
                      height: "1.5px",
                      background:
                        "radial-gradient(circle, var(--accent) 0%, color-mix(in srgb, var(--accent) 40%, transparent) 40%, transparent 75%)",
                      boxShadow: "0 0 16px 3px color-mix(in srgb, var(--accent) 25%, transparent)",
                      animation: "_wo-flare 3s ease-in-out infinite alternate",
                      willChange: "transform, opacity",
                    }}
                  />
                )}
              </m.div>
            );
          })}
        </AnimatePresence>
      </div>

      {/* ─── Reveal Prompt (Stage 3 only) ─── */}
      {activeStage === 3 && !isSSR && (
        <m.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: EASE_OUT, delay: 1.0 }}
          style={{
            position: "absolute",
            bottom: "15%",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "6px",
            fontFamily: "var(--font-sans, system-ui, sans-serif)",
            fontSize: "0.75rem",
            fontWeight: 500,
            letterSpacing: "0.14em",
            textTransform: "uppercase",
            color: "var(--muted)",
            animation: "_wo-bounce 2s ease-in-out infinite",
            cursor: "pointer",
            willChange: "transform",
          }}
        >
          <span>Reveal Homepage</span>
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ opacity: 0.7 }}
          >
            <line x1="12" y1="5" x2="12" y2="19" />
            <polyline points="19 12 12 19 5 12" />
          </svg>
        </m.div>
      )}

      {/* ─── Skip Hint (Visible during stages 1-2) ─── */}
      {!reducedMotion && !isSSR && stage < 3 && (
        <m.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.55 }}
          transition={{ delay: 0.5, duration: 0.4, ease: "easeOut" }}
          style={{
            position: "absolute",
            bottom: "4%",
            fontFamily: "var(--font-sans, system-ui, sans-serif)",
            fontSize: "0.75rem",
            fontWeight: 400,
            letterSpacing: "0.05em",
            color: "var(--muted)",
            pointerEvents: "none",
            willChange: "opacity",
          }}
        >
          Click anywhere to skip
        </m.div>
      )}

      {/* ─── Progress Indicators ─── */}
      <div
        style={{
          display: "flex",
          gap: "10px",
          position: "absolute",
          bottom: "7%",
          left: "50%",
          transform: "translateX(-50%)",
          zIndex: 10,
        }}
      >
        {[1, 2, 3].map((i) => {
          const isActive = activeStage >= i;
          const isCurrent = activeStage === i;
          return (
            <div
              key={i}
              style={{
                width: "28px",
                height: "2px",
                backgroundColor: isActive
                  ? "var(--foreground)"
                  : "color-mix(in srgb, var(--foreground) 15%, transparent)",
                opacity: isCurrent ? 1 : isActive ? 0.5 : 0.3,
                transition: "all 0.6s cubic-bezier(0.4, 0, 0.2, 1)",
                boxShadow: isCurrent
                  ? "0 0 8px 1px color-mix(in srgb, var(--accent) 35%, transparent)"
                  : "none",
              }}
            />
          );
        })}
        </div>
      </m.div>
      )}
    </AnimatePresence>
  );
}
