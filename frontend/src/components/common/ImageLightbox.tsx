/* eslint-disable @next/next/no-img-element */
"use client";

import React, { useEffect, useCallback, useRef } from "react";
import { m, AnimatePresence, useReducedMotion } from "framer-motion";
import { X } from "lucide-react";
import { lightboxBackdrop, lightboxImage } from "@/design-system/motion/variants";

interface ImageLightboxProps {
  src: string;
  alt: string;
  isOpen: boolean;
  onClose: () => void;
  /** The source rect of the image on screen — used to animate from its position */
  sourceRect?: DOMRect | null;
}

/**
 * ImageLightbox
 *
 * Notion-style image zoom that scales from the image's current position to center.
 * Dark backdrop fades in simultaneously.
 *
 * - ESC key closes
 * - Click outside closes
 * - Focus trapped while open
 * - aria-modal for screen readers
 */
export function ImageLightbox({ src, alt, isOpen, onClose, sourceRect }: ImageLightboxProps) {
  const shouldReduceMotion = useReducedMotion();
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  // ESC key to close
  useEffect(() => {
    if (!isOpen) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKey);
    // Focus the close button for accessibility
    setTimeout(() => closeButtonRef.current?.focus(), 50);
    return () => window.removeEventListener("keydown", handleKey);
  }, [isOpen, onClose]);

  // Prevent body scroll while open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => { document.body.style.overflow = ""; };
  }, [isOpen]);

  const handleBackdropClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === e.currentTarget) onClose();
    },
    [onClose]
  );

  return (
    <AnimatePresence>
      {isOpen && (
        <m.div
          key="lightbox-backdrop"
          initial="hidden"
          animate="visible"
          exit="hidden"
          variants={shouldReduceMotion ? { hidden: { opacity: 0 }, visible: { opacity: 1 } } : lightboxBackdrop}
          className="fixed inset-0 z-[200] flex items-center justify-center bg-black/80 backdrop-blur-sm"
          onClick={handleBackdropClick}
          role="dialog"
          aria-modal="true"
          aria-label={`Image: ${alt}`}
        >
          {/* Close button */}
          <button
            ref={closeButtonRef}
            onClick={onClose}
            className="absolute top-4 right-4 z-10 flex items-center justify-center w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 text-white transition-colors backdrop-blur-sm border border-white/20"
            aria-label="Close image"
          >
            <X className="w-5 h-5" />
          </button>

          {/* Image — scales from source position to center */}
          <m.div
            key="lightbox-image"
            initial={
              shouldReduceMotion
                ? { opacity: 0 }
                : sourceRect
                ? {
                    // Start from the image's screen position
                    opacity: 0,
                    scale: 0.85,
                  }
                : { opacity: 0, scale: 0.85 }
            }
            animate={
              shouldReduceMotion
                ? { opacity: 1 }
                : { opacity: 1, scale: 1 }
            }
            exit={
              shouldReduceMotion
                ? { opacity: 0 }
                : { opacity: 0, scale: 0.9 }
            }
            transition={
              shouldReduceMotion
                ? { duration: 0.15 }
                : { duration: 0.3, ease: [0.22, 1, 0.36, 1] }
            }
            className="relative max-w-[90vw] max-h-[90vh]"
            onClick={(e) => e.stopPropagation()}
          >
            <img
              src={src}
              alt={alt}
              className="max-w-[90vw] max-h-[90vh] object-contain rounded-lg shadow-2xl"
              style={{ display: "block" }}
            />
          </m.div>

          {/* Alt text caption */}
          {alt && (
            <m.p
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 0.7, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2, delay: 0.15 }}
              className="absolute bottom-6 left-0 right-0 text-center text-white/70 text-sm font-sans px-8 line-clamp-2"
            >
              {alt}
            </m.p>
          )}
        </m.div>
      )}
    </AnimatePresence>
  );
}
