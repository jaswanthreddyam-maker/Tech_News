"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { Moon } from "lucide-react";

interface ThemeToggleProps {
  variant?: "button" | "dropdown" | "settings";
}

export function ThemeToggle({ variant = "dropdown" }: ThemeToggleProps) {
  if (variant === "settings") {
    return (
      <div className="flex items-center justify-between p-3 rounded-xl border border-white/15 bg-white/[0.04] text-foreground">
        <div className="flex items-center gap-2.5">
          <Moon className="w-4 h-4 text-primary" />
          <span className="text-xs font-semibold">OLED Dark Mode</span>
        </div>
        <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400">
          Locked
        </span>
      </div>
    );
  }

  return (
    <Button
      variant="ghost"
      size="icon"
      className="h-9 w-9 rounded-full relative text-foreground border border-white/10 bg-white/[0.04] hover:bg-white/[0.10] hover:border-white/20 transition-all duration-300 shadow-sm cursor-default"
      title="Dark Mode Active"
    >
      <Moon className="h-4 w-4 text-primary" />
      <span className="sr-only">Dark mode active</span>
    </Button>
  );
}
