"use client";

import React, { useEffect, useState, useMemo } from "react";
import { List } from "lucide-react";
import { cn } from "@/lib/utils";

interface TableOfContentsProps {
  selector?: string; // e.g., "article.prose"
}

interface HeadingInfo {
  id: string;
  text: string;
  level: number;
  element: HTMLElement;
}

export function TableOfContents({ selector = "article" }: TableOfContentsProps) {
  const [headings, setHeadings] = useState<HeadingInfo[]>([]);
  const [activeId, setActiveId] = useState<string>("");

  useEffect(() => {
    // Wait for the DOM content to be present
    const elements = Array.from(document.querySelectorAll(`${selector} h2, ${selector} h3`)) as HTMLElement[];
    
    const parsedHeadings = elements.map((el, index) => {
      // Ensure element has an ID
      if (!el.id) {
        el.id = `heading-${index}`;
      }
      return {
        id: el.id,
        text: el.innerText,
        level: Number(el.tagName.charAt(1)),
        element: el,
      };
    });

    setHeadings(parsedHeadings);

    if (parsedHeadings.length === 0) return;

    // Set up IntersectionObserver
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id);
          }
        });
      },
      { rootMargin: "0px 0px -80% 0px" } // trigger when heading is near the top
    );

    elements.forEach((el) => observer.observe(el));

    return () => observer.disconnect();
  }, [selector]);

  const memoizedHeadings = useMemo(() => headings, [headings]);

  if (memoizedHeadings.length === 0) return null;

  return (
    <div className="bg-card border border-border rounded-xl p-5 space-y-5 sticky top-24">
      <div className="flex items-center gap-2 border-b border-border/50 pb-4">
        <List className="w-4 h-4 text-muted-foreground" />
        <h3 className="font-sans font-bold text-sm text-foreground tracking-tight">
          In this article
        </h3>
      </div>

      <nav className="max-h-[60vh] overflow-y-auto scrollbar-thin">
        <ul className="space-y-3">
          {memoizedHeadings.map((heading, index) => (
            <li 
              key={`${heading.id}-${index}`} 
              style={{ paddingLeft: `${(heading.level - 2) * 12}px` }}
            >
              <a
                href={`#${heading.id}`}
                className={cn(
                  "block text-sm transition-colors",
                  activeId === heading.id 
                    ? "text-primary font-bold" 
                    : "text-muted-foreground hover:text-foreground"
                )}
                onClick={(e) => {
                  e.preventDefault();
                  heading.element.scrollIntoView({ behavior: "smooth", block: "start" });
                }}
              >
                {heading.text}
              </a>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}
