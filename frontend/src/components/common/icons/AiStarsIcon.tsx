import * as React from "react";

export function AiStarsIcon({
  className = "w-6 h-6",
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
      {/* Main Large Star (Left) */}
      <path d="M9.5 3.5C9.5 8 5.5 11.5 1.5 12C5.5 12.5 9.5 16 9.5 20.5C9.5 16 13.5 12.5 17.5 12C13.5 11.5 9.5 8 9.5 3.5Z" />

      {/* Top-Right Star */}
      <path d="M18 1.5C18 4.2 15.8 6.2 13.5 6.5C15.8 6.8 18 8.8 18 11.5C18 8.8 20.2 6.8 22.5 6.5C20.2 6.2 18 4.2 18 1.5Z" />

      {/* Bottom-Right Star */}
      <path d="M17.5 13.5C17.5 16 15.5 17.8 13.5 18C15.5 18.2 17.5 20 17.5 22.5C17.5 20 19.5 18.2 21.5 18C19.5 17.8 17.5 16 17.5 13.5Z" />
    </svg>
  );
}
