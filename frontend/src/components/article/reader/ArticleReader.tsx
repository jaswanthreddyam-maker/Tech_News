"use client";

import React, { useMemo, useEffect, useRef } from "react";
import { useReadingPreferences } from "./ReadingPreferences";
import "@/styles/prose-theme.css";

interface ArticleReaderProps {
  content: string;
}

/**
 * ArticleReader
 *
 * Renders article HTML content with:
 * - Heading IDs + anchor links for TOC
 * - Single batched IntersectionObserver for block-level reveals
 *   (H2, H3, blockquote, figure, pre only — NOT paragraphs)
 * - Reading preference CSS variable hooks
 *
 * The observer is created ONCE for the entire article, not per-element.
 * This is both performant and avoids the "70 paragraphs → 70 animations" problem.
 */
export function ArticleReader({ content }: ArticleReaderProps) {
  const { mounted } = useReadingPreferences();
  const containerRef = useRef<HTMLDivElement>(null);

  // Process heading IDs for TOC and anchor link support
  const processedContent = useMemo(() => {
    if (typeof window === "undefined") return content;

    try {
      const parser = new DOMParser();
      const doc = parser.parseFromString(content, "text/html");
      const headings = doc.querySelectorAll("h2, h3, h4");

      headings.forEach((el, index) => {
        if (!el.id) {
          const textContent = el.textContent || "";
          const slug = textContent
            .toLowerCase()
            .replace(/[^\w\s-]/g, "")
            .replace(/\s+/g, "-")
            .replace(/^-+|-+$/g, "");
          el.id = slug || `section-${index}`;
        }

        // Add hover-reveal anchor link
        if (!el.querySelector(".prose-theme-heading-link")) {
          const anchor = doc.createElement("a");
          anchor.href = `#${el.id}`;
          anchor.className = "prose-theme-heading-link";
          anchor.innerText = "¶";
          anchor.setAttribute("aria-hidden", "true");
          anchor.setAttribute("tabindex", "-1");
          el.appendChild(anchor);
        }
      });

      return doc.body.innerHTML;
    } catch (e) {
      console.error("Error processing article headings:", e);
      return content;
    }
  }, [content]);

  // Single batched IntersectionObserver — block-level only
  // Targets: h2, h3, blockquote, figure, pre (NOT p — avoids 70-animations problem)
  useEffect(() => {
    if (!containerRef.current || typeof window === "undefined") return;

    // Respect prefers-reduced-motion
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) return;

    const BLOCK_SELECTOR = "h2, h3, blockquote, figure, pre";
    const elements = containerRef.current.querySelectorAll<HTMLElement>(BLOCK_SELECTOR);

    if (elements.length === 0) return;

    // ONE observer for ALL block-level elements
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            (entry.target as HTMLElement).classList.add("block-revealed");
            // Unobserve after reveal — never replays
            observer.unobserve(entry.target);
          }
        });
      },
      {
        root: null,
        rootMargin: "0px 0px -10% 0px", // trigger slightly before edge
        threshold: 0.1,
      }
    );

    elements.forEach((el) => {
      // Mark as needing reveal (CSS sets initial hidden state)
      el.classList.add("block-reveal-pending");
      observer.observe(el);
    });

    return () => observer.disconnect();
  }, [processedContent, mounted]);

  return (
    <div
      ref={containerRef}
      // prose-theme picks up --reader-* CSS variables for font, size, spacing, max-width
      className="prose-theme"
      dangerouslySetInnerHTML={{ __html: processedContent }}
    />
  );
}
