import React from "react";
import { 
  Cpu, 
  ShieldAlert, 
  Rocket, 
  Briefcase, 
  Globe, 
  Newspaper,
  Terminal,
  LucideIcon
} from "lucide-react";

interface Theme {
  icon: LucideIcon;
  gradient: string;
  label: string;
}

const THUMBNAIL_THEMES: Record<string, Theme> = {
  "Artificial Intelligence": {
    icon: Cpu,
    gradient: "from-blue-950 via-indigo-950 to-violet-950",
    label: "AI",
  },
  "Cybersecurity": {
    icon: ShieldAlert,
    gradient: "from-emerald-950 via-teal-950 to-cyan-950",
    label: "Cyber",
  },
  "Robotics": {
    icon: Rocket,
    gradient: "from-orange-950 via-red-950 to-rose-950",
    label: "Robotics",
  },
  "Startups": {
    icon: Briefcase,
    gradient: "from-fuchsia-950 via-purple-950 to-pink-950",
    label: "Startups",
  },
  "Space & Science": {
    icon: Globe,
    gradient: "from-slate-950 via-gray-950 to-zinc-950",
    label: "Science",
  },
  "Software Development": {
    icon: Terminal,
    gradient: "from-sky-950 via-blue-950 to-indigo-950",
    label: "Software",
  },
  "Synthetic Test": {
    icon: Cpu,
    gradient: "from-rose-950 via-red-900 to-pink-950",
    label: "Test",
  },
  "default": {
    icon: Newspaper,
    gradient: "from-neutral-950 via-stone-950 to-zinc-950",
    label: "News",
  }
};

interface Props {
  category?: string;
  className?: string;
}

export function CategoryPlaceholder({ category, className = "" }: Props) {
  const theme = THUMBNAIL_THEMES[category || ""] || THUMBNAIL_THEMES["default"];
  const Icon = theme.icon;

  return (
    <div className={`relative flex flex-col items-center justify-center w-full h-full bg-gradient-to-br ${theme.gradient} overflow-hidden ${className}`}>
      {/* Subtle Grid Background overlay */}
      <div 
        className="absolute inset-0 opacity-20 pointer-events-none"
        style={{
          backgroundImage: "linear-gradient(to right, rgba(255,255,255,0.05) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.05) 1px, transparent 1px)",
          backgroundSize: "20px 20px"
        }}
      />
      
      {/* Radial Category Glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-40 h-40 rounded-full bg-white/5 blur-2xl pointer-events-none" />

      {/* Glassmorphic card overlay */}
      <div className="absolute inset-0 bg-white/[0.03] border border-white/10 backdrop-blur-sm pointer-events-none" />

      {/* Icon and Label */}
      <div className="relative z-10 flex flex-col items-center justify-center gap-2 text-white/80 select-none">
        <div className="p-3 rounded-xl bg-white/5 border border-white/10 shadow-lg backdrop-blur-md">
          <Icon className="w-8 h-8 stroke-[1.5] drop-shadow-md text-white/90" />
        </div>
        <span className="mt-1 text-[10px] font-bold tracking-[0.2em] uppercase text-white/60">{theme.label}</span>
      </div>

      {/* Branded Platform Watermark */}
      <div className="absolute bottom-2 left-0 right-0 text-center pointer-events-none select-none z-10">
        <span className="text-[9px] font-black tracking-[0.3em] text-white/15 uppercase">
          Tech News Today
        </span>
      </div>
    </div>
  );
}
