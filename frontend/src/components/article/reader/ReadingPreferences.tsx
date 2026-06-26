"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Settings2, Type, AlignLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export interface ReadingConfig {
  font: "serif" | "sans";
  size: number;        // px: 16 | 18 | 20 | 22
  spacing: "normal" | "relaxed" | "loose";
}

const STORAGE_KEY = "tnt_reading_preferences";

const FONT_FAMILIES = {
  serif: "'Georgia', 'Times New Roman', serif",
  sans: "'Inter', system-ui, -apple-system, sans-serif",
};

const SIZE_STEPS = [16, 18, 20, 22];

const SPACING_MAP = {
  normal:  { lineHeight: "1.6", paragraphSpacing: "1.25rem" },
  relaxed: { lineHeight: "1.8", paragraphSpacing: "1.5rem" },
  loose:   { lineHeight: "2.0", paragraphSpacing: "1.75rem" },
};

// Width scales with font size for comfortable reading ergonomics
const WIDTH_MAP: Record<number, string> = {
  16: "70ch",
  18: "72ch",
  20: "76ch",
  22: "80ch",
};

const DEFAULT_CONFIG: ReadingConfig = {
  font: "serif",
  size: 18,
  spacing: "relaxed",
};

/** Applies reading config as CSS custom properties on documentElement.
 *  Called on mount (from stored prefs) and on every user change. */
function applyConfigToDOM(config: ReadingConfig) {
  const root = document.documentElement;
  root.style.setProperty("--reader-font-family", FONT_FAMILIES[config.font]);
  root.style.setProperty("--reader-font-size", `${config.size / 16}rem`);
  root.style.setProperty("--reader-line-height", SPACING_MAP[config.spacing].lineHeight);
  root.style.setProperty("--reader-paragraph-spacing", SPACING_MAP[config.spacing].paragraphSpacing);
  root.style.setProperty("--reader-max-width", WIDTH_MAP[config.size] ?? "72ch");
}

// Helper hook — shared by ReadingPreferences and ArticleReader
export function useReadingPreferences() {
  const [config, setConfig] = useState<ReadingConfig>(DEFAULT_CONFIG);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed: ReadingConfig = JSON.parse(stored);
        setConfig(parsed);
        applyConfigToDOM(parsed);
      } else {
        applyConfigToDOM(DEFAULT_CONFIG);
      }
    } catch {
      applyConfigToDOM(DEFAULT_CONFIG);
    }
  }, []);

  const updateConfig = useCallback((updates: Partial<ReadingConfig>) => {
    setConfig((prev) => {
      const next = { ...prev, ...updates };
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {}
      applyConfigToDOM(next);
      return next;
    });
  }, []);

  return { config, updateConfig, mounted };
}

export function ReadingPreferences() {
  const { config, updateConfig, mounted } = useReadingPreferences();

  if (!mounted) return null;

  const sizeIndex = SIZE_STEPS.indexOf(config.size);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="gap-2 text-xs font-mono tracking-wider h-8 border-border/50 text-muted-foreground hover:bg-foreground hover:text-background focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-2"
          aria-label="Reading preferences"
        >
          <Settings2 className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Preferences</span>
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent
        align="end"
        className="w-68 bg-card border-border shadow-lg"
        onCloseAutoFocus={(e) => e.preventDefault()}
      >
        <DropdownMenuLabel className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          Typography
        </DropdownMenuLabel>
        <DropdownMenuSeparator className="bg-border/50" />

        <div className="p-3 space-y-5">

          {/* ── Typeface ── */}
          <div className="space-y-2">
            <span className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground block">
              Typeface
            </span>
            <div className="grid grid-cols-2 gap-2">
              {(["serif", "sans"] as const).map((f) => (
                <button
                  key={f}
                  onClick={() => updateConfig({ font: f })}
                  className={[
                    "h-8 rounded-md border text-xs transition-all duration-150",
                    "focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring",
                    f === "serif" ? "font-serif" : "font-sans",
                    config.font === f
                      ? "bg-foreground text-background border-foreground font-semibold"
                      : "border-border text-muted-foreground hover:text-foreground hover:border-foreground/40",
                  ].join(" ")}
                >
                  {f === "serif" ? "Serif" : "Sans"}
                </button>
              ))}
            </div>
          </div>

          {/* ── Font Size ── */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
                Size
              </span>
              <span className="text-[10px] font-mono text-muted-foreground tabular-nums">
                {config.size}px
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Type className="w-3 h-3 text-muted-foreground shrink-0" />
              <input
                type="range"
                min={0}
                max={SIZE_STEPS.length - 1}
                step={1}
                value={sizeIndex < 0 ? 1 : sizeIndex}
                onChange={(e) => {
                  updateConfig({ size: SIZE_STEPS[parseInt(e.target.value)] });
                }}
                className="flex-1 h-1.5 accent-foreground cursor-pointer"
                aria-label="Font size"
              />
              <Type className="w-5 h-5 text-foreground shrink-0" />
            </div>
            <div className="flex justify-between px-5">
              {SIZE_STEPS.map((s) => (
                <span
                  key={s}
                  className={`text-[9px] font-mono tabular-nums transition-colors ${
                    config.size === s ? "text-foreground font-bold" : "text-muted-foreground/50"
                  }`}
                >
                  {s}
                </span>
              ))}
            </div>
          </div>

          {/* ── Line Spacing ── */}
          <div className="space-y-2">
            <span className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground block">
              Spacing
            </span>
            <div className="grid grid-cols-3 gap-2">
              {(["normal", "relaxed", "loose"] as const).map((s) => (
                <button
                  key={s}
                  onClick={() => updateConfig({ spacing: s })}
                  className={[
                    "h-8 rounded-md border text-[10px] uppercase tracking-wide transition-all duration-150",
                    "focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring",
                    config.spacing === s
                      ? "bg-foreground text-background border-foreground font-semibold"
                      : "border-border text-muted-foreground hover:text-foreground hover:border-foreground/40",
                  ].join(" ")}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          {/* ── Reading Width indicator ── */}
          <div className="pt-1 border-t border-border/40">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <AlignLeft className="w-3 h-3 text-muted-foreground" />
                <span className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
                  Width
                </span>
              </div>
              <span className="text-[10px] font-mono text-muted-foreground">
                {WIDTH_MAP[config.size] ?? "72ch"}
              </span>
            </div>
          </div>

        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
