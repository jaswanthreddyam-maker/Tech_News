import * as React from "react";

export function Sliders2Icon({
  className = "h-4 w-4",
  strokeWidth = 2,
}: {
  className?: string;
  strokeWidth?: number;
}) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {/* Top slider track & knob on the right */}
      <line x1="3" x2="12.5" y1="7.5" y2="7.5" />
      <circle cx="16" cy="7.5" r="3.5" />
      <line x1="19.5" x2="21" y1="7.5" y2="7.5" />

      {/* Bottom slider track & knob on the left */}
      <line x1="3" x2="4.5" y1="16.5" y2="16.5" />
      <circle cx="8" cy="16.5" r="3.5" />
      <line x1="11.5" x2="21" y1="16.5" y2="16.5" />
    </svg>
  );
}
