"use client";

import { Reveal, StaggerContainer, StaggerItem } from "@/components/animations";

/* eslint-disable react/jsx-no-comment-textnodes, @typescript-eslint/no-unused-vars */
export function StoryEvolution() {
  const mockTimeline = [
    { id: 1, time: "09:14", label: "First Report", source: "Bloomberg", current: false },
    { id: 2, time: "10:01", label: "Reuters Update", source: "Reuters", current: false },
    { id: 3, time: "10:07", label: "Current Summary", source: "AI Synthesized", current: true },
  ];

  return (
    <div className="py-8 border-t border-border mt-8">
      <Reveal>
        <h2 className="text-2xl font-sans font-bold tracking-tight mb-6">Story Evolution</h2>
      </Reveal>
      <div className="p-6 border border-border bg-neutral-950 rounded-xl relative">
        <div className="absolute left-10 top-8 bottom-8 w-px bg-neutral-800" />
        
        <StaggerContainer className="space-y-6 relative z-10">
          {mockTimeline.map((item, idx) => (
            <StaggerItem key={item.id} className="flex gap-6 items-start">
              {/* Timestamp */}
              <div className="w-12 text-right shrink-0 pt-0.5">
                <span className={`text-[10px] font-mono tracking-wider ${item.current ? "text-white" : "text-neutral-400"}`}>
                  {item.time}
                </span>
              </div>
              
              {/* Node */}
              <div className="relative flex flex-col items-center">
                <div className={`w-3 h-3 rounded-full mt-1.5 outline outline-4 outline-neutral-950 ${item.current ? "bg-primary shadow-[0_0_10px_rgba(var(--primary),0.5)]" : "bg-neutral-700"}`} />
              </div>
              
              {/* Content */}
              <div className="flex-1 pb-2">
                <h4 className={`text-sm font-sans font-bold ${item.current ? "text-white" : "text-neutral-400"}`}>
                  {item.label}
                </h4>
                <p className="text-[10px] uppercase font-mono tracking-widest text-neutral-400 mt-1">
                  {item.source}
                </p>
              </div>
            </StaggerItem>
          ))}
        </StaggerContainer>
      </div>
    </div>
  );
}
