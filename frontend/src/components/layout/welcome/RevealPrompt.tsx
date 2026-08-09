"use client";

import { m } from "framer-motion";

const EASE_OUT: [number, number, number, number] = [0, 0, 0.2, 1];

export function RevealPrompt() {
  return (
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
  );
}
