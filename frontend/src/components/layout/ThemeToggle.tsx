"use client";

import * as React from "react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";
import { Sun, Moon, Monitor, Check } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface ThemeToggleProps {
  variant?: "button" | "dropdown" | "settings";
}

export function ThemeToggle({ variant = "dropdown" }: ThemeToggleProps) {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => setMounted(true), []);

  if (variant === "settings") {
    const options = [
      { id: "dark", label: "Dark", icon: Moon },
      { id: "light", label: "Light", icon: Sun },
      { id: "system", label: "System", icon: Monitor },
    ];

    return (
      <div className="grid grid-cols-3 gap-3">
        {options.map((opt) => {
          const Icon = opt.icon;
          const isSelected = mounted && theme === opt.id;
          return (
            <button
              key={opt.id}
              type="button"
              onClick={() => setTheme(opt.id)}
              className={`flex flex-col items-center justify-center p-3 rounded-xl border text-center transition-all duration-300 relative group cursor-pointer ${
                isSelected
                  ? "bg-primary/10 border-primary text-foreground shadow-sm"
                  : "bg-white/[0.03] border-white/10 hover:border-white/20 text-muted-foreground hover:text-foreground"
              }`}
            >
              {isSelected && (
                <span className="absolute top-1.5 right-1.5 w-3.5 h-3.5 rounded-full bg-primary flex items-center justify-center text-primary-foreground">
                  <Check className="w-2 h-2" strokeWidth={3} />
                </span>
              )}
              <Icon className={`w-4 h-4 mb-1.5 transition-transform duration-300 group-hover:scale-110 ${isSelected ? "text-primary" : ""}`} />
              <span className="text-xs font-semibold">{opt.label}</span>
            </button>
          );
        })}
      </div>
    );
  }

  if (!mounted) {
    return (
      <Button
        variant="ghost"
        size="icon"
        className="h-9 w-9 rounded-full border border-white/10 bg-white/[0.04] text-foreground"
      >
        <Sun className="h-4 w-4" />
        <span className="sr-only">Toggle theme</span>
      </Button>
    );
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9 rounded-full relative text-foreground border border-white/10 bg-white/[0.04] hover:bg-white/[0.10] hover:border-white/20 hover:-translate-y-[1px] transition-all duration-300 shadow-sm group"
        >
          <Sun className="h-4 w-4 rotate-0 scale-100 transition-all duration-300 group-hover:rotate-[15deg] dark:-rotate-90 dark:scale-0 text-foreground" />
          <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all duration-300 group-hover:rotate-[15deg] dark:rotate-0 dark:scale-100 text-foreground" />
          <span className="sr-only">Toggle theme</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-[140px] bg-background/90 backdrop-blur-xl border border-white/15 text-foreground shadow-2xl rounded-xl">
        <DropdownMenuItem onClick={() => setTheme("dark")} className="gap-2 cursor-pointer rounded-lg hover:bg-white/10">
          <Moon className="h-4 w-4 text-foreground" /> Dark
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme("system")} className="gap-2 cursor-pointer rounded-lg hover:bg-white/10">
          <Monitor className="h-4 w-4 text-foreground" /> System
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme("light")} className="gap-2 cursor-pointer rounded-lg hover:bg-white/10">
          <Sun className="h-4 w-4 text-foreground" /> Light
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
