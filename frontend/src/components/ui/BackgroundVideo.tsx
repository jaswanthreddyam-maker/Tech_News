"use client";

import React, { useEffect, useRef, useState } from "react";

interface BackgroundVideoProps {
  src?: string;
  className?: string;
  overlayClassName?: string;
  opacity?: number;
}

/**
 * BackgroundVideo — High-visibility cinematic video background playing seamlessly across all sections.
 */
export function BackgroundVideo({
  src = "/videos/bg-video.mp4",
  className = "",
  overlayClassName = "",
  opacity = 0.8,
}: BackgroundVideoProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    video.defaultMuted = true;
    video.muted = true;

    const attemptPlay = () => {
      const playPromise = video.play();
      if (playPromise !== undefined) {
        playPromise
          .then(() => {
            setIsPlaying(true);
          })
          .catch(() => {
            // Autoplay blocked by browser policy: retry on first user interaction
            const handleInteract = () => {
              video.play().then(() => setIsPlaying(true)).catch(() => {});
              window.removeEventListener("click", handleInteract);
              window.removeEventListener("scroll", handleInteract);
              window.removeEventListener("touchstart", handleInteract);
              window.removeEventListener("keydown", handleInteract);
            };
            window.addEventListener("click", handleInteract, { once: true });
            window.addEventListener("scroll", handleInteract, { once: true });
            window.addEventListener("touchstart", handleInteract, { once: true });
            window.addEventListener("keydown", handleInteract, { once: true });
          });
      }
    };

    attemptPlay();
  }, [src]);

  return (
    <div
      className={`fixed inset-0 pointer-events-none z-0 overflow-hidden select-none bg-black ${className}`}
      aria-hidden="true"
    >
      {/* Cinematic Background Video Element */}
      <video
        ref={videoRef}
        autoPlay
        loop
        muted
        playsInline
        preload="auto"
        controls={false}
        disablePictureInPicture
        disableRemotePlayback
        onCanPlay={() => {
          if (videoRef.current) {
            videoRef.current.play().then(() => setIsPlaying(true)).catch(() => {});
          }
        }}
        className="w-full h-full object-cover transition-opacity duration-700 scale-105"
        style={{
          opacity,
          transform: "translate3d(0, 0, 0)",
          backfaceVisibility: "hidden",
        }}
      >
        <source src={src} type="video/mp4" />
      </video>

      {/* Subtle Contrast & Vignette Overlays for Crisp Text Legibility */}
      <div
        className={`absolute inset-0 bg-gradient-to-b from-black/60 via-transparent to-black/75 pointer-events-none ${overlayClassName}`}
      />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_20%,rgba(0,0,0,0.6)_100%)] pointer-events-none" />
    </div>
  );
}

/**
 * SectionVideoBackground — Embedded container for individual section frames
 */
export function SectionVideoBackground({
  src = "/videos/bg-video.mp4",
  className = "",
  opacity = 0.75,
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
      video.defaultMuted = true;
      video.muted = true;
      video.play().catch(() => {});
    }
  }, [src]);

  return (
    <div className={`relative overflow-hidden rounded-3xl border border-white/15 bg-black/40 backdrop-blur-xl ${className}`}>
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
        <div className="absolute inset-0 bg-gradient-to-b from-black/50 via-transparent to-black/70" />
      </div>

      {/* Foreground Content */}
      <div className="relative z-10 w-full">
        {children}
      </div>
    </div>
  );
}
