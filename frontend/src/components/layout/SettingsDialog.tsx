"use client";

import * as React from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Settings, Moon, Eye } from "lucide-react";

interface SettingsDialogProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  trigger?: React.ReactNode;
}

export function SettingsDialog({ open, onOpenChange, trigger }: SettingsDialogProps) {


  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {trigger && <DialogTrigger asChild>{trigger}</DialogTrigger>}
      <DialogContent className="sm:max-w-[460px] bg-background/95 backdrop-blur-2xl border border-white/15 text-foreground shadow-2xl rounded-2xl p-6">
        <DialogHeader className="space-y-1 pb-4 border-b border-white/10">
          <div className="flex items-center gap-2 text-primary font-mono text-xs uppercase tracking-widest font-semibold">
            <Settings className="w-4 h-4" />
            <span>Preferences</span>
          </div>
          <DialogTitle className="text-xl font-bold font-sans">Settings</DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground font-mono">
            Customize your AI newsroom appearance and preferences.
          </DialogDescription>
        </DialogHeader>

        {/* Appearance & Theme Section */}
        <div className="py-4 space-y-4">
          <div className="space-y-1">
            <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground/80 flex items-center gap-2">
              <Eye className="w-3.5 h-3.5 text-primary" />
              <span>Appearance</span>
            </h4>
            <p className="text-xs text-muted-foreground">
              Tech News Today operates exclusively in OLED Dark Theme.
            </p>
          </div>

          <div className="pt-1">
            <div className="flex items-center justify-between p-4 rounded-xl border border-white/15 bg-white/[0.04] text-foreground shadow-sm">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-white/10 flex items-center justify-center text-primary">
                  <Moon className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-xs font-bold font-sans">Dark Theme (Locked)</div>
                  <div className="text-[11px] text-muted-foreground font-mono">Pitch OLED dark aesthetic</div>
                </div>
              </div>
              <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-semibold uppercase bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                Active
              </span>
            </div>
          </div>
        </div>

      </DialogContent>
    </Dialog>
  );
}
