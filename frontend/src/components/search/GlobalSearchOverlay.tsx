"use client";

import { useEffect } from "react";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { CommandPalette } from "./CommandPalette";

export function GlobalSearchOverlay({ open, onOpenChange }: { open: boolean, onOpenChange: (o: boolean) => void }) {
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        onOpenChange(!open);
      }
      if (e.key === "/" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        onOpenChange(!open);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, [open, onOpenChange]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl p-0 overflow-hidden bg-transparent border-none shadow-none gap-0">
        <DialogTitle className="sr-only">Command Palette</DialogTitle>
        <div className="w-full h-full">
          <CommandPalette onSelect={() => onOpenChange(false)} />
        </div>
      </DialogContent>
    </Dialog>
  );
}
