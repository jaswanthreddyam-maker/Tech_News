"use client";

import { useEffect, useState, useRef, useCallback, useReducer } from "react";
import { m, AnimatePresence } from "framer-motion";
import { OverlayParticles } from "./welcome/OverlayParticles";
import { OverlayProgress } from "./welcome/OverlayProgress";
import { RevealPrompt } from "./welcome/RevealPrompt";
import { SkipHint } from "./welcome/SkipHint";

interface WelcomeOverlayClientProps {
  isMounted: boolean;
  hasPlayed: boolean | null;
  onComplete: () => void;
}

export type OverlayState = "intro" | "stage1" | "stage2" | "stage3" | "skipping" | "finished";

type OverlayAction =
  | { type: "SET_STAGE"; stage: OverlayState }
  | { type: "SKIP" }
  | { type: "FINISH" };

function overlayReducer(state: OverlayState, action: OverlayAction): OverlayState {
  switch (action.type) {
    case "SET_STAGE":
      if (state === "skipping" || state === "finished") return state;
      return action.stage;
    case "SKIP":
      if (state === "finished") return state;
      return state === "stage3" ? "finished" : "skipping";
    case "FINISH":
      return "finished";
    default:
      return state;
  }
}

const STAGES: { state: OverlayState; delay: number }[] = [
  { state: "stage1", delay: 0 },
  { state: "stage2", delay: 400 },
  { state: "stage3", delay: 900 },
];

const AUTO_REVEAL_AT = 3000;

const BLUR_VARIANTS = {
  enter: { opacity: 0, filter: "blur(16px)", scale: 0.97, y: 12 },
  visible: { opacity: 1, filter: "blur(0px)", scale: 1, y: 0 },
  exit: { opacity: 0, filter: "blur(16px)", scale: 0.97, y: 8 },
};

const FADE_VARIANTS = {
  enter: { opacity: 0 },
  visible: { opacity: 1 },
  exit: { opacity: 0 },
};

const EASE_IN_OUT: [number, number, number, number] = [0.4, 0, 0.2, 1];
const EASE_OUT: [number, number, number, number] = [0, 0, 0.2, 1];
const PEEL_EASE: [number, number, number, number] = [0.76, 0, 0.24, 1];

const WORDS: { text: string; stage: OverlayState; isBrand?: boolean }[] = [
  { text: "Welcome", stage: "stage1" },
  { text: "To", stage: "stage2" },
  { text: "Tech-News Today", stage: "stage3", isBrand: true },
];

export default function WelcomeOverlayClient({
  isMounted,
  hasPlayed,
  onComplete,
}: WelcomeOverlayClientProps) {
  const [overlayState, dispatch] = useReducer(overlayReducer, "intro");
  const [reducedMotion, setReducedMotion] = useState(false);
  const completedRef = useRef(false);
  const overlayRef = useRef<HTMLDivElement>(null);

  // Synchronous state ref for event handlers
  const stateRef = useRef(overlayState);
  stateRef.current = overlayState;

  // Detect reduced-motion preference
  useEffect(() => {
    const mql = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(mql.matches);
    const handler = (e: MediaQueryListEvent) => setReducedMotion(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);

  const doComplete = useCallback(() => {
    if (completedRef.current) return;
    completedRef.current = true;
    if (typeof document !== "undefined") {
      document.body.style.overflow = "";
    }
    try {
      sessionStorage.setItem("welcome-played", "1");
    } catch {}
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event("welcome-overlay-complete"));
    }
    dispatch({ type: "FINISH" });
    onComplete();
  }, [onComplete]);

  const handleSkip = useCallback(
    (e?: Event) => {
      if (completedRef.current) return;

      if (e instanceof KeyboardEvent && (e.key === " " || e.key === "Enter")) {
        e.preventDefault();
      }

      dispatch({ type: "SKIP" });
      doComplete();
    },
    [doComplete]
  );

  const doCompleteRef = useRef(doComplete);
  useEffect(() => {
    doCompleteRef.current = doComplete;
  }, [doComplete]);

  // Timeline & Scroll lock effect
  useEffect(() => {
    if (!isMounted || hasPlayed === true) return;

    document.body.style.overflow = "hidden";
    window.scrollTo(0, 0);

    if (reducedMotion) {
      dispatch({ type: "SET_STAGE", stage: "stage3" });
      const t = setTimeout(() => doCompleteRef.current(), 800);
      return () => {
        clearTimeout(t);
        document.body.style.overflow = "";
      };
    }

    const timers = STAGES.map(({ state, delay }) =>
      setTimeout(() => dispatch({ type: "SET_STAGE", stage: state }), delay)
    );
    timers.push(setTimeout(() => doCompleteRef.current(), AUTO_REVEAL_AT));

    return () => {
      timers.forEach(clearTimeout);
      document.body.style.overflow = "";
    };
  }, [isMounted, hasPlayed, reducedMotion]);

  // Global skip listener
  useEffect(() => {
    if (!isMounted || hasPlayed === true || completedRef.current) return;

    const handleInteraction = (e: Event) => {
      if (e instanceof MouseEvent || e instanceof PointerEvent) {
        if (e.button !== 0) return;
      }
      // On mobile tap or desktop click, only allow skipping after stage 3 ("Tech-News Today") is active
      if (stateRef.current !== "stage3") return;
      handleSkip(e);
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " " || e.key === "Escape") {
        handleSkip(e);
      }
    };

    const events: [string, EventListener, boolean?][] = [
      ["mousedown", handleInteraction as EventListener, true],
      ["touchstart", handleInteraction as EventListener, true],
      ["keydown", handleKeyDown as EventListener, true],
    ];

    events.forEach(([type, fn, capture]) =>
      window.addEventListener(type, fn, { capture, passive: type === "touchstart" })
    );

    return () => {
      events.forEach(([type, fn, capture]) =>
        window.removeEventListener(type, fn, { capture })
      );
    };
  }, [isMounted, hasPlayed, handleSkip]);

  // Focus trap accessibility
  useEffect(() => {
    if (isMounted && hasPlayed === false && overlayRef.current) {
      overlayRef.current.focus();
    }
  }, [isMounted, hasPlayed]);

  const isSSR = !isMounted || hasPlayed === null;
  const isVisible = overlayState !== "finished";
  const isSkipping = overlayState === "skipping";
  const activeStage = isSSR || overlayState === "intro" ? "stage1" : overlayState;

  const stageNumberMap: Record<OverlayState, number> = {
    intro: 1,
    stage1: 1,
    stage2: 2,
    stage3: 3,
    skipping: 1,
    finished: 3,
  };
  const activeStageNumber = stageNumberMap[activeStage];

  const variants = reducedMotion ? FADE_VARIANTS : BLUR_VARIANTS;
  const wordDuration = reducedMotion ? 0.25 : 0.35;

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
          onClick={() => activeStage === "stage3" && doComplete()}
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
            cursor: activeStage === "stage3" ? "pointer" : "default",
            willChange: "transform, opacity",
          }}
        >
          <OverlayParticles />

          {/* Center Stage Word Display */}
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
            <AnimatePresence>
              {WORDS.map((word) => {
                if (activeStage !== word.stage) return null;

                return (
                  <m.div
                    key={`word-${word.stage}`}
                    initial={isSSR ? { opacity: 1 } : variants.enter}
                    animate={variants.visible}
                    exit={variants.exit}
                    transition={{ duration: wordDuration, ease: EASE_IN_OUT }}
                    style={{
                      position: "absolute",
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
                        textShadow:
                          "0 0 40px color-mix(in srgb, var(--accent) 20%, transparent)",
                        lineHeight: 1.1,
                      }}
                    >
                      {word.text}
                    </h1>

                    {(word.stage === "stage1" || word.stage === "stage3") && (
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
                          boxShadow:
                            "0 0 16px 3px color-mix(in srgb, var(--accent) 25%, transparent)",
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

          {activeStage === "stage3" && !isSSR && <RevealPrompt />}

          {!reducedMotion && !isSSR && activeStage !== "stage3" && <SkipHint />}

          <OverlayProgress activeStageNumber={activeStageNumber} />
        </m.div>
      )}
    </AnimatePresence>
  );
}
