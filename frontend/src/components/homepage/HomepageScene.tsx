"use client";

import React from "react";
import { BackgroundVideo } from "@/components/ui/BackgroundVideo";

interface HomepageSceneProps {
  children: React.ReactNode;
}

/**
 * HomepageScene — Cinematic Ambient Video & Spatial Scene
 */
export function HomepageScene({ children }: HomepageSceneProps) {
  return (
    <div className="relative w-full min-h-screen bg-transparent text-foreground overflow-x-clip select-none">
      {/* Background Video Environment */}
      <BackgroundVideo />

      {/* Spatial Section Content */}
      <div className="relative z-10 w-full flex flex-col items-center">
        {children}
      </div>
    </div>
  );
}
