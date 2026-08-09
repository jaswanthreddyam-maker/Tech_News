"use client";

import { useMemo } from "react";

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

export function OverlayParticles() {
  const particles = useMemo(
    () =>
      PARTICLES.map((p, i) => (
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
      )),
    []
  );

  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden", pointerEvents: "none" }}>
      {particles}
    </div>
  );
}
