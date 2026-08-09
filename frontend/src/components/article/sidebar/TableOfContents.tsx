"use client";

import React, { useEffect, useState, useMemo } from "react";
import { List } from "lucide-react";
import { cn } from "@/lib/utils";

interface TableOfContentsProps {
  selector?: string;
}

interface HeadingInfo {
  id: string;
  text: string;
  level: number;
  element: HTMLElement;
}

/**
 * Clean HTML heading text by stripping anchor markers like ¶, #, and trailing whitespace
 */
function sanitizeHeadingText(rawText: string): string {
  if (!rawText) return "";
  return rawText
    .replace(/[¶#]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

export function TableOfContents({ selector = "article" }: TableOfContentsProps) {
  const [headings, setHeadings] = useState<HeadingInfo[]>([]);
  const [activeId, setActiveId] = useState<string>("");

  useEffect(() => {
    const elements = Array.from(
      document.querySelectorAll(`${selector} h2, ${selector} h3`)
    ) as HTMLElement[];

    const parsedHeadings: HeadingInfo[] = [];

    elements.forEach((el, index) => {
      const cleanText = sanitizeHeadingText(el.innerText);
      
      // Filter out empty or trivial headings
      if (!cleanText || cleanText.length < 2) return;

      if (!el.id) {
        el.id = `heading-${index}`;
      }

      parsedHeadings.push({
        id: el.id,
        text: cleanText,
        level: Number(el.tagName.charAt(1)),
        element: el,
      });
    });

    setHeadings(parsedHeadings);

    if (parsedHeadings.length < 2) return;

    // Trigger active state when heading is near the top of viewport
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id);
          }
        });
      },
      { rootMargin: "0px 0px -75% 0px" }
    );

    elements.forEach((el) => observer.observe(el));

    return () => observer.disconnect();
  }, [selector]);

  const memoizedHeadings = useMemo(() => headings, [headings]);

  // Hide entire panel if fewer than 2 valid headings exist
  if (memoizedHeadings.length < 2) return null;

  return (
    <div className="bg-card/40 border border-border/50 rounded-xl p-4 space-y-3 shadow-sm">
      <div className="flex items-center gap-2 border-b border-border/40 pb-2.5">
        <List className="w-3.5 h-3.5 text-primary" strokeWidth={1.75} />
        <h3 className="font-mono font-medium text-[11px] uppercase tracking-wider text-muted-foreground">
          In this article
        </h3>
      </div>

      <nav className="max-h-[300px] overflow-y-auto scrollbar-thin pr-1">
        <ul className="space-y-1.5 font-sans">
          {memoizedHeadings.map((heading, index) => {
            const isActive = activeId === heading.id;
            const isH3 = heading.level === 3;

            return (
              <li
                key={`${heading.id}-${index}`}
                className={cn("transition-all", isH3 ? "pl-3" : "pl-0")}
              >
                <a
                  href={`#${heading.id}`}
                  className={cn(
                    "group flex items-start gap-2 text-xs py-1.5 px-2 rounded-lg transition-all leading-relaxed line-clamp-2",
                    isActive
                      ? "text-primary font-bold bg-primary/10 border-l-2 border-primary"
                      : "text-muted-foreground/80 hover:text-foreground hover:bg-muted/20"
                  )}
                  onClick={(e) => {
                    e.preventDefault();
                    heading.element.scrollIntoView({
                      behavior: "smooth",
                      block: "start",
                    });
                  }}
                >
                  <span className="shrink-0 mt-1 text-[10px]">
                    {isActive ? (
                      <span className="text-primary font-bold">●</span>
                    ) : isH3 ? (
                      <span className="text-muted-foreground/40">•</span>
                    ) : (
                      <span className="text-muted-foreground/60">○</span>
                    )}
                  </span>

                  <span className="min-w-0">{heading.text}</span>
                </a>
              </li>
            );
          })}
        </ul>
      </nav>
    </div>
  );
}
