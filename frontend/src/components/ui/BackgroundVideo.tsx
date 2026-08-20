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
  opacity = 1,
}: BackgroundVideoProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    video.defaultMuted = true;
    video.muted = true;
    video.playbackRate = 1.0;

    const playVideo = () => {
      const playPromise = video.play();
      if (playPromise !== undefined) {
        playPromise
          .then(() => setIsPlaying(true))
          .catch(() => {
            // Autoplay retry on user interaction or visibility change
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

    const handleVisibility = () => {
      if (document.visibilityState === "visible") {
        playVideo();
      }
    };

    playVideo();
    document.addEventListener("visibilitychange", handleVisibility);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [src]);

  return (
    <div
      className={`fixed inset-0 pointer-events-none z-0 overflow-hidden select-none ${className}`}
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
        onLoadedMetadata={(e) => {
          const v = e.currentTarget;
          v.muted = true;
          v.play().then(() => setIsPlaying(true)).catch(() => {});
        }}
        onCanPlay={(e) => {
          const v = e.currentTarget;
          v.muted = true;
          v.play().then(() => setIsPlaying(true)).catch(() => {});
        }}
        className="w-full h-full object-cover transition-opacity duration-500 scale-[1.02]"
        style={{
          opacity,
          filter: "brightness(1.2) contrast(1.15)",
          transform: "translate3d(0, 0, 0)",
          backfaceVisibility: "hidden",
        }}
      >
        <source src={src} type="video/mp4" />
      </video>

      {/* Subtle Ambient Blend Overlay */}
      <div
        className={`absolute inset-0 bg-gradient-to-b from-black/20 via-transparent to-black/30 pointer-events-none ${overlayClassName}`}
      />
    </div>
  );
}

/**
 * SectionVideoBackground — Embedded container for individual section frames
 */
export function SectionVideoBackground({
  src = "/videos/bg-video.mp4",
  className = "",
  opacity = 1,
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
    <div className={`relative overflow-hidden rounded-3xl border border-white/15 bg-black/30 backdrop-blur-xl ${className}`}>
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
          style={{ opacity, filter: "brightness(1.15) contrast(1.1)" }}
        >
          <source src={src} type="video/mp4" />
        </video>
        <div className="absolute inset-0 bg-gradient-to-b from-black/20 via-transparent to-black/30" />
      </div>

      {/* Foreground Content */}
      <div className="relative z-10 w-full">
        {children}
      </div>
    </div>
  );
}
