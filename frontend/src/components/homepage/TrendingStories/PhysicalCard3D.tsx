"use client";

import React from "react";
import { TrendingUp } from "lucide-react";
import { PhysicalWalls } from "./PhysicalWalls";

interface PhysicalCard3DProps {
  children?: React.ReactNode;
  frontFace?: React.ReactNode;
  backFace?: React.ReactNode;
  lighting?: React.ReactNode;
  walls?: React.ReactNode;
  thickness?: number;
  roundedClass?: string;
  className?: string;
  frontFaceClassName?: string;
}

/**
 * PhysicalCard3D — Pure 3D Physical Geometry Primitive
 * Owns 3D Slab Geometry (FrontFace, BackFace). Exposes slots for frontFace, backFace, lighting, and walls.
 * Pure geometric primitive with zero lighting, navigation, or tilt coupling.
 */
export function PhysicalCard3D({
  children,
  frontFace,
  backFace,
  lighting,
  walls,
  thickness = 14,
  roundedClass = "rounded-[18px]",
  className = "",
  frontFaceClassName = "",
}: PhysicalCard3DProps) {
  const activeFrontFace = frontFace || children;
  const activeWalls = walls || <PhysicalWalls thickness={thickness} />;

  return (
    <div
      className={`group relative w-full h-full ${className}`}
      style={{
        transformStyle: "preserve-3d",
      }}
    >
      {/* 1. FRONT FACE CONTAINER (Physical Front Surface) */}
      <div
        className={`group/front relative w-full h-full ${roundedClass} ${frontFaceClassName} transition-[background-color,border-color,box-shadow] duration-300 ease-out motion-reduce:transform-none motion-reduce:transition-none`}
        style={{
          transformStyle: "preserve-3d",
          backfaceVisibility: "hidden",
          WebkitBackfaceVisibility: "hidden",
          transform: "translateZ(0px)",
        }}
      >
        {activeFrontFace}
      </div>

      {/* 2. BACK FACE CONTAINER (Physical Back Surface) */}
      <div
        className={`absolute inset-0 ${roundedClass} bg-[#07080b] border border-white/15 flex flex-col items-center justify-center overflow-hidden pointer-events-none`}
        style={{
          transformStyle: "preserve-3d",
          backfaceVisibility: "hidden",
          WebkitBackfaceVisibility: "hidden",
          transform: `translateZ(-${thickness}px) rotateY(180deg)`,
          boxShadow:
            "0 24px 60px rgba(0,0,0,0.95), inset 0 0 0 1px rgba(255,255,255,0.08)",
        }}
      >
        {backFace || (
          <>
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(255,255,255,0.04)_0%,transparent_70%)]" />
            <div
              className="flex flex-col items-center gap-2.5 opacity-25"
              style={{ transform: "translateZ(1px)" }}
            >
              <TrendingUp className="w-8 h-8 text-white" strokeWidth={1.5} />
              <span className="text-[10px] font-mono tracking-[0.2em] text-white font-bold uppercase">
                Tech News Today
              </span>
            </div>
          </>
        )}
      </div>

      {/* 3. OPTIONAL LIGHTING LAYER SLOT */}
      {lighting}

      {/* 4. SIDE WALLS SLOT */}
      {activeWalls}
    </div>
  );
}
