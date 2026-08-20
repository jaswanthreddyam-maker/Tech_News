"use client";

import React from "react";

interface HomepageSceneProps {
  children: React.ReactNode;
}

/**
 * HomepageScene — Pitch OLED Black Environment
 */
export function HomepageScene({ children }: HomepageSceneProps) {
  return (
    <div className="relative w-full min-h-screen bg-black text-foreground overflow-x-clip select-none">
      {/* Layer 1: Pure OLED Black Environment */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden bg-black" />

      {/* Layer 2: Seamless Spatial Content */}
      <div className="relative z-10 w-full flex flex-col items-center">
        {children}
      </div>
    </div>
  );
}
