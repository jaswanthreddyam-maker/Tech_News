"use client";

interface OverlayProgressProps {
  activeStageNumber: number;
}

export function OverlayProgress({ activeStageNumber }: OverlayProgressProps) {
  return (
    <div
      style={{
        display: "flex",
        gap: "10px",
        position: "absolute",
        bottom: "clamp(36px, 6vh, 48px)",
        left: "50%",
        transform: "translateX(-50%)",
        zIndex: 10,
      }}
    >
      {[1, 2, 3].map((i) => {
        const isActive = activeStageNumber >= i;
        const isCurrent = activeStageNumber === i;
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
  );
}
