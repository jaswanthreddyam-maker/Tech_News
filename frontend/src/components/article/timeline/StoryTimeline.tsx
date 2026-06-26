import React from "react";
import { GitCommit } from "lucide-react";

export interface TimelineEvent {
  id: number;
  time: string;
  label: string;
  source: string;
  current: boolean;
}

interface StoryTimelineProps {
  events: TimelineEvent[] | null;
}

export function StoryTimeline({ events }: StoryTimelineProps) {
  if (events === null) {
    return (
      <div className="py-8 border-t border-border mt-8">
        <h2 className="text-2xl font-sans font-bold tracking-tight mb-6 text-[#111827]">Story Evolution</h2>
        <div 
          className="py-8 border rounded-[24px] relative"
          style={{
            background: "linear-gradient(180deg, #FFF5EC 0%, #FEEFE1 100%)",
            borderColor: "#E9D8C7",
            boxShadow: "0 10px 30px rgba(0,0,0,0.05)",
            paddingLeft: "48px",
            paddingRight: "48px"
          }}
        >
          <p className="text-sm text-[#6B7280] text-center">
            No timeline available for this article.
          </p>
        </div>
      </div>
    );
  }

  if (events.length === 0) {
    return null; // Backend supports it but no events yet
  }

  return (
    <div className="py-8 border-t border-border mt-8">
      <h2 className="text-2xl font-sans font-bold tracking-tight mb-6 text-[#111827]">Story Evolution</h2>

      <div 
        className="py-8 border rounded-[24px] relative"
        style={{
          background: "linear-gradient(180deg, #FFF5EC 0%, #FEEFE1 100%)",
          borderColor: "#E9D8C7",
          boxShadow: "0 10px 30px rgba(0,0,0,0.05)",
          paddingLeft: "48px",
          paddingRight: "48px"
        }}
      >
        <div className="absolute left-[126px] top-10 bottom-10 w-px" style={{ backgroundColor: "rgba(0,0,0,0.08)" }} />
        
        <div className="space-y-8 relative z-10">
          {events.map((item) => (
            <div key={item.id} className="flex gap-6 items-start -mx-2 p-2">
              {/* Timestamp */}
              <div className="w-12 text-right shrink-0 pt-0.5">
                <span className="text-[10px] font-mono tracking-wider text-[#9CA3AF]">
                  {item.time}
                </span>
              </div>
              
              {/* Node */}
              <div className="relative flex flex-col items-center">
                <div className={`w-3 h-3 rounded-full mt-1.5 outline outline-4 outline-[#FEEFE1] ${item.current ? "bg-[#111111]" : "bg-[#B8B8B8]"}`} />
              </div>
              
              {/* Content */}
              <div className="flex-1 pb-2">
                <h4 className="text-sm font-sans font-bold text-[#1F2937]">
                  {item.label}
                </h4>
                <p className="text-[10px] uppercase font-mono tracking-widest text-[#6B7280] mt-1">
                  {item.source}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
