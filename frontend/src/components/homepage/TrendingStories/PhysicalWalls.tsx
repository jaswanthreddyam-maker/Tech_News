"use client";

import React from "react";

interface PhysicalWallsProps {
  thickness?: number;
}

/**
 * PhysicalWalls — Enterprise Decoupled 3D Slab Extrusion Wall Primitive
 * Manages Top, Bottom, Left, and Right 3D side wall faces.
 * Isolated from 3D slab geometry container.
 */
export function PhysicalWalls({ thickness = 14 }: PhysicalWallsProps) {
  return (
    <>
      {/* Top Wall */}
      <div
        className="absolute left-3 right-3 top-0 origin-top pointer-events-none"
        style={{
          height: thickness,
          transformStyle: "preserve-3d",
          backfaceVisibility: "hidden",
          WebkitBackfaceVisibility: "hidden",
          transform: "rotateX(-90deg)",
          background:
            "linear-gradient(to bottom, rgba(255,255,255,0.35) 0%, rgba(255,255,255,0.08) 1px, #1c1d22 2px, #060608 100%)",
        }}
      />
      {/* Bottom Wall */}
      <div
        className="absolute left-3 right-3 bottom-0 origin-bottom pointer-events-none"
        style={{
          height: thickness,
          transformStyle: "preserve-3d",
          backfaceVisibility: "hidden",
          WebkitBackfaceVisibility: "hidden",
          transform: "rotateX(90deg)",
          background:
            "linear-gradient(to top, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0.02) 1px, #0a0b0e 2px, #020202 100%)",
        }}
      />
      {/* Left Wall */}
      <div
        className="absolute top-3 bottom-3 left-0 origin-left pointer-events-none"
        style={{
          width: thickness,
          transformStyle: "preserve-3d",
          backfaceVisibility: "hidden",
          WebkitBackfaceVisibility: "hidden",
          transform: "rotateY(90deg)",
          background:
            "linear-gradient(to right, rgba(255,255,255,0.25) 0%, rgba(255,255,255,0.05) 1px, #16171c 2px, #050507 100%)",
        }}
      />
      {/* Right Wall */}
      <div
        className="absolute top-3 bottom-3 right-0 origin-right pointer-events-none"
        style={{
          width: thickness,
          transformStyle: "preserve-3d",
          backfaceVisibility: "hidden",
          WebkitBackfaceVisibility: "hidden",
          transform: "rotateY(-90deg)",
          background:
            "linear-gradient(to left, rgba(255,255,255,0.25) 0%, rgba(255,255,255,0.05) 1px, #16171c 2px, #050507 100%)",
        }}
      />
    </>
  );
}
