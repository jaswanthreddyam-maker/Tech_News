"use client";

import * as React from "react";
import { useTheme } from "next-themes";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Settings, Sun, Moon, Monitor, Check, Eye } from "lucide-react";

interface SettingsDialogProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  trigger?: React.ReactNode;
}

export function SettingsDialog({ open, onOpenChange, trigger }: SettingsDialogProps) {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => setMounted(true), []);

  const themes = [
    {
      id: "dark",
      label: "Dark",
      icon: Moon,
      description: "Pitch OLED dark aesthetic",
    },
    {
      id: "light",
      label: "Light",
      icon: Sun,
      description: "Clean high-contrast light mode",
    },
    {
      id: "system",
      label: "System",
      icon: Monitor,
      description: "Sync with OS preference",
    },
  ];

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

        {/* Appearance & Theme Toggle Section */}
        <div className="py-4 space-y-4">
          <div className="space-y-1">
            <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground/80 flex items-center gap-2">
              <Eye className="w-3.5 h-3.5 text-primary" />
              <span>Appearance & Theme</span>
            </h4>
            <p className="text-xs text-muted-foreground">
              Select your preferred color scheme for reading stories.
            </p>
          </div>

          <div className="grid grid-cols-3 gap-3 pt-1">
            {themes.map((t) => {
              const Icon = t.icon;
              const isSelected = mounted && theme === t.id;

              return (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setTheme(t.id)}
                  className={`flex flex-col items-center justify-center p-3.5 rounded-xl border text-center transition-all duration-300 relative group cursor-pointer ${
                    isSelected
                      ? "bg-primary/10 border-primary text-foreground shadow-[0_0_15px_rgba(255,255,255,0.1)]"
                      : "bg-white/[0.03] border-white/10 hover:border-white/20 text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {isSelected && (
                    <span className="absolute top-2 right-2 w-4 h-4 rounded-full bg-primary flex items-center justify-center text-primary-foreground">
                      <Check className="w-2.5 h-2.5" strokeWidth={3} />
                    </span>
                  )}
                  <Icon className={`w-5 h-5 mb-2 transition-transform duration-300 group-hover:scale-110 ${isSelected ? "text-primary" : ""}`} />
                  <span className="text-xs font-semibold">{t.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
