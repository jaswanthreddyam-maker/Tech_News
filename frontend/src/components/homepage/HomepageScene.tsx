"use client";

import React from "react";

interface HomepageSceneProps {
  children: React.ReactNode;
}

/**
 * HomepageScene — Spatial Scene Wrapper
 */
export function HomepageScene({ children }: HomepageSceneProps) {
  return (
    <div className="relative w-full min-h-screen bg-transparent text-foreground overflow-x-clip select-none">
      {/* Spatial Section Content */}
      <div className="relative z-10 w-full flex flex-col items-center">
        {children}
      </div>
    </div>
  );
}
