"use client";

import * as React from "react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";
import { Sun, Moon, Monitor } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function ThemeToggle() {
  const { setTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => setMounted(true), []);

  if (!mounted) {
    return (
      <Button variant="ghost" size="icon" className="h-8 w-8 text-foreground">
        <Sun className="h-4 w-4" />
        <span className="sr-only">Toggle theme</span>
      </Button>
    );
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="h-8 w-8 relative text-foreground transition-colors hover:bg-neutral-100 dark:hover:bg-neutral-800">
          <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0 text-foreground" />
          <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100 text-foreground" />
          <span className="sr-only">Toggle theme</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-[140px] bg-card border border-border text-foreground">
        <DropdownMenuItem onClick={() => setTheme("dark")} className="gap-2 cursor-pointer hover:bg-accent hover:text-accent-foreground">
          <Moon className="h-4 w-4 text-foreground" /> Dark
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme("system")} className="gap-2 cursor-pointer hover:bg-accent hover:text-accent-foreground">
          <Monitor className="h-4 w-4 text-foreground" /> System
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme("light")} className="gap-2 cursor-pointer hover:bg-accent hover:text-accent-foreground">
          <Sun className="h-4 w-4 text-foreground" /> Light
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
