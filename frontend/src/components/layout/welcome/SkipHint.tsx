"use client";

import { m } from "framer-motion";

export function SkipHint() {
  return (
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
  );
}
