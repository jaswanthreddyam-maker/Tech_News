"use client";

import React from "react";
import { Badge } from "@/components/ui/badge";
import { BadgeConfig } from "@/domains/article/presentation";
import {
  Newspaper,
  CircleDot,
  LayoutGrid,
  MessageSquareQuote,
  BookOpen,
  Radio,
  FileText,
} from "lucide-react";

const ICON_MAP = {
  newspaper: Newspaper,
  "circle-dot": CircleDot,
  "layout-grid": LayoutGrid,
  "message-square-quote": MessageSquareQuote,
  "book-open": BookOpen,
  radio: Radio,
  "file-text": FileText,
};

interface CardHeaderProps {
  badge?: BadgeConfig;
  category?: string | { name?: string } | null;
  className?: string;
}

export function CardHeader({ badge, category, className = "" }: CardHeaderProps) {
  const catName = typeof category === "string" ? category : category?.name;
  const IconComp = badge ? ICON_MAP[badge.iconName] || Newspaper : Newspaper;

  return (
    <div className={`flex flex-wrap items-center gap-2 text-xs font-mono uppercase tracking-wider ${className}`}>
      {badge && (
        <Badge variant="outline" className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 font-bold ${badge.className}`}>
          <IconComp className="w-3.5 h-3.5 shrink-0" strokeWidth={1.75} />
          <span>{badge.label}</span>
        </Badge>
      )}
      {catName && (
        <span className="text-muted-foreground/80 font-medium">
          {catName}
        </span>
      )}
    </div>
  );
}
