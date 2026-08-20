"use client";

import React, { useEffect, useRef } from "react";

interface BackgroundVideoProps {
  src?: string;
  className?: string;
  overlayClassName?: string;
  opacity?: number;
}

/**
 * BackgroundVideo — High-performance persistent cinematic video background
 * optimized for OLED/Dark themes with zero main-thread jank.
 */
export function BackgroundVideo({
  src = "/videos/bg-video.mp4",
  className = "",
  overlayClassName = "",
  opacity = 0.45,
}: BackgroundVideoProps) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    // Ensure video plays smoothly across all browser autoplay policies
    const video = videoRef.current;
    if (video) {
      video.muted = true;
      const playPromise = video.play();
      if (playPromise !== undefined) {
        playPromise.catch(() => {
          // Autoplay blocked fallback or retry on interaction
          const handleFirstInteraction = () => {
            video.play().catch(() => {});
            window.removeEventListener("click", handleFirstInteraction);
            window.removeEventListener("scroll", handleFirstInteraction);
            window.removeEventListener("touchstart", handleFirstInteraction);
          };
          window.addEventListener("click", handleFirstInteraction, { once: true });
          window.addEventListener("scroll", handleFirstInteraction, { once: true });
          window.addEventListener("touchstart", handleFirstInteraction, { once: true });
        });
      }
    }
  }, []);

  return (
    <div
      className={`fixed inset-0 pointer-events-none z-0 overflow-hidden select-none ${className}`}
      aria-hidden="true"
    >
      {/* Video stream element */}
      <video
        ref={videoRef}
        autoPlay
        loop
        muted
        playsInline
        preload="auto"
        className="w-full h-full object-cover transition-opacity duration-1000 scale-[1.02]"
        style={{
          opacity,
          transform: "translate3d(0, 0, 0)",
          backfaceVisibility: "hidden",
        }}
      >
        <source src={src} type="video/mp4" />
      </video>

      {/* Cinematic Vignette & Ambient Darkness Overlays */}
      <div
        className={`absolute inset-0 bg-gradient-to-b from-black/80 via-black/45 to-black/90 pointer-events-none ${overlayClassName}`}
      />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_0%,rgba(0,0,0,0.75)_100%)] pointer-events-none" />
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808006_1px,transparent_1px),linear-gradient(to_bottom,#80808006_1px,transparent_1px)] bg-[size:32px_32px] opacity-30 pointer-events-none" />
    </div>
  );
}

/**
 * SectionVideoBackground — Embedded video background container for individual section frames
 */
export function SectionVideoBackground({
  src = "/videos/bg-video.mp4",
  className = "",
  opacity = 0.35,
  children,
}: {
  src?: string;
  className?: string;
  opacity?: number;
  children?: React.ReactNode;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (video) {
      video.muted = true;
      video.play().catch(() => {});
    }
  }, []);

  return (
    <div className={`relative overflow-hidden rounded-3xl border border-white/10 bg-black/40 backdrop-blur-md ${className}`}>
      {/* Background Video */}
      <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden">
        <video
          ref={videoRef}
          autoPlay
          loop
          muted
          playsInline
          preload="auto"
          className="w-full h-full object-cover"
          style={{ opacity }}
        >
          <source src={src} type="video/mp4" />
        </video>
        <div className="absolute inset-0 bg-gradient-to-b from-black/70 via-black/30 to-black/80" />
      </div>

      {/* Foreground Content */}
      <div className="relative z-10 w-full">
        {children}
      </div>
    </div>
  );
}
