"use client";

import React from "react";

interface PhysicalLightingProps {
  roundedClass?: string;
  specularClassName?: string;
}

/**
 * PhysicalLighting — Enterprise Decoupled Lighting Layer
 * Manages Specular Edge Highlight and Dynamic Cursor-Tracking Glare Sheen.
 * Isolated from 3D geometry primitive.
 */
export function PhysicalLighting({
  roundedClass = "rounded-[18px]",
  specularClassName = "right-6 w-24 group-hover:w-36",
}: PhysicalLightingProps) {
  return (
    <>
      {/* Specular Edge Highlight Bar */}
      <div
        className={`absolute -top-[1px] ${specularClassName} h-[1.5px] bg-gradient-to-r from-transparent via-white/90 to-transparent group-hover:via-white transition-all duration-500 z-20 pointer-events-none`}
        style={{ transform: "translateZ(2px)" }}
      />

      {/* Dynamic Cursor-Tracking Glare Sheen Overlay */}
      <div
        className={`absolute inset-0 ${roundedClass} pointer-events-none opacity-40 group-hover:opacity-90 transition-opacity duration-300 z-20`}
        style={{
          transform: "translateZ(2px)",
          background:
            "radial-gradient(circle at var(--card-light-x, 50%) var(--card-light-y, 50%), rgba(255,255,255,0.22) 0%, rgba(255,255,255,0.04) 40%, transparent 75%)",
        }}
      />
    </>
  );
}
