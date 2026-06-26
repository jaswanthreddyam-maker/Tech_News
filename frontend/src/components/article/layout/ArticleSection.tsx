import React from "react";
import { cn } from "@/lib/utils";

export interface ArticleSectionProps {
  children: React.ReactNode;
  className?: string;
  bordered?: boolean;
  title?: string;
  compact?: boolean;
  padding?: boolean | string;
}

export function ArticleSection({
  children,
  className,
  bordered = false,
  title,
  compact = false,
  padding = false,
}: ArticleSectionProps) {
  const paddingClass = typeof padding === "string" 
    ? padding 
    : padding 
      ? "p-6 md:p-8" 
      : "";

  return (
    <div className={cn("w-full", className)}>
      {bordered && <div className="h-px bg-border/15 w-full mb-8" />}
      <div className={cn("w-full", compact ? "space-y-2" : "space-y-4", paddingClass)}>
        {title && (
          <h3 className="font-mono text-xs uppercase tracking-wider text-muted-foreground font-semibold">
            {title}
          </h3>
        )}
        <div className="w-full">
          {children}
        </div>
      </div>
    </div>
  );
}
