"use client";

import React, { useMemo } from "react";
import { useReadingPreferences } from "./ReadingPreferences";
import "@/styles/prose-theme.css";

interface ArticleReaderProps {
  content: string; // The HTML content
}

export function ArticleReader({ content }: ArticleReaderProps) {
  const { mounted } = useReadingPreferences();

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

  // Show skeleton while preferences are loading to avoid FOUC
  if (!mounted) {
    return (
      <div className="animate-pulse flex flex-col gap-4 max-w-[72ch]" aria-hidden>
        <div className="h-5 bg-muted/60 rounded w-full" />
        <div className="h-5 bg-muted/60 rounded w-11/12" />
        <div className="h-5 bg-muted/60 rounded w-4/6" />
        <div className="h-5 bg-muted/40 rounded w-full mt-2" />
        <div className="h-5 bg-muted/40 rounded w-5/6" />
      </div>
    );
  }

  return (
    <div
      // prose-theme picks up --reader-* CSS variables for font, size, spacing, max-width
      className="prose-theme"
      dangerouslySetInnerHTML={{ __html: processedContent }}
    />
  );
}
