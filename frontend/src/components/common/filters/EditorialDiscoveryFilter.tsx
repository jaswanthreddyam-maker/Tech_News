"use client";

import React from "react";
import {
  LayoutGrid,
  Zap,
  Mail,
  MessageSquare,
  Star,
  LucideIcon,
} from "lucide-react";

export type DiscoveryFilterType =
  | "all"
  | "breaking_news"
  | "newsletter"
  | "roundup"
  | "opinion"
  | "review";

export interface FilterTabOption {
  key: DiscoveryFilterType;
  label: string;
  icon: LucideIcon;
  count?: number;
}

export const DISCOVERY_FILTER_OPTIONS: FilterTabOption[] = [
  { key: "all", label: "All Stories", icon: LayoutGrid },
  { key: "breaking_news", label: "Breaking", icon: Zap },
  { key: "newsletter", label: "Newsletters", icon: Mail },
  { key: "roundup", label: "Roundups", icon: LayoutGrid },
  { key: "opinion", label: "Opinion", icon: MessageSquare },
  { key: "review", label: "Reviews", icon: Star },
];

interface EditorialDiscoveryFilterProps {
  activeFilter: DiscoveryFilterType;
  onFilterChange: (filter: DiscoveryFilterType) => void;
  filterCounts?: Partial<Record<DiscoveryFilterType, number>>;
  className?: string;
}

export function EditorialDiscoveryFilter({
  activeFilter,
  onFilterChange,
  filterCounts,
  className = "",
}: EditorialDiscoveryFilterProps) {
  return (
    <div
      aria-label="Filter content by document type"
      className={`flex items-center gap-2.5 overflow-x-auto pb-1 pt-1 scrollbar-none ${className}`}
    >
      {DISCOVERY_FILTER_OPTIONS.map((tab) => {
        const isActive = activeFilter === tab.key;
        const count = filterCounts?.[tab.key];
        const IconComponent = tab.icon;

        return (
          <button
            key={tab.key}
            type="button"
            onClick={() => onFilterChange(tab.key)}
            className={`
              inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-sans tracking-tight transition-all duration-200 shrink-0 border
              ${
                isActive
                  ? "bg-[#0e1d17] text-emerald-400 border-emerald-500/40 font-semibold shadow-[0_0_12px_rgba(16,185,129,0.12)]"
                  : "bg-[#13161a] text-zinc-300 hover:text-white border-[#20252c] hover:border-zinc-700 font-medium hover:bg-[#1a1e24]"
              }
            `}
          >
            <IconComponent
              className={`w-3.5 h-3.5 transition-colors ${
                isActive
                  ? "text-emerald-400"
                  : "text-zinc-400 group-hover:text-zinc-200"
              }`}
              strokeWidth={1.75}
            />
            <span>{tab.label}</span>
            {count !== undefined && count > 0 && (
              <span
                className={`ml-1 text-[10px] px-1.5 py-0.2 rounded-full ${
                  isActive
                    ? "bg-emerald-500/20 text-emerald-300"
                    : "bg-white/10 text-muted-foreground"
                }`}
              >
                {count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
