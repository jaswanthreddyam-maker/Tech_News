"use client";

import { Reveal, StaggerContainer, StaggerItem } from "@/components/animations";
import { m } from "framer-motion";
import { MotionScales } from "@/design-system/motion/tokens";
import { useState, useEffect } from "react";
import { Skeleton } from "@/design-system/components/Skeleton";
import { useLoadingState } from "@/design-system/hooks/useLoadingState";

/* eslint-disable react/jsx-no-comment-textnodes, @typescript-eslint/no-unused-vars */
export function StoryEvolution() {
  const mockTimeline = [
    { id: 1, time: "09:14", label: "First Report", source: "Bloomberg", current: false },
    { id: 2, time: "10:01", label: "Reuters Update", source: "Reuters", current: false },
    { id: 3, time: "10:07", label: "Current Summary", source: "AI Synthesized", current: true },
  ];

  const [isLoading, setIsLoading] = useState(true);
  useEffect(() => {
    const timer = setTimeout(() => setIsLoading(false), 1500);
    return () => clearTimeout(timer);
  }, []);

  const loadingLevel = useLoadingState(isLoading);

  if (isLoading) {
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
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex gap-6 items-start rounded-xl p-2 -mx-2">
                <div className="w-12 text-right shrink-0 pt-0.5 flex justify-end">
                  <Skeleton level={loadingLevel} className="h-3 w-8" />
                </div>
                <div className="relative flex flex-col items-center">
                  <Skeleton level={loadingLevel} className="w-3 h-3 rounded-full mt-1.5" />
                </div>
                <div className="flex-1 pb-2">
                  <Skeleton level={loadingLevel} className="h-4 w-32 mb-2" />
                  <Skeleton level={loadingLevel} className="h-3 w-20" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="py-8 border-t border-border mt-8">
      <Reveal>
        <h2 className="text-2xl font-sans font-bold tracking-tight mb-6 text-[#111827]">Story Evolution</h2>
      </Reveal>
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
        
        <StaggerContainer className="space-y-8 relative z-10">
          {mockTimeline.map((item, idx) => (
            <StaggerItem key={item.id} className="relative">
              <m.div
                whileHover={{ scale: MotionScales.card }}
                whileTap={{ scale: MotionScales.tap }}
                className="flex gap-6 items-start rounded-xl hover:bg-black/5 p-2 transition-colors cursor-default -mx-2"
              >
                {/* Timestamp */}
                <div className="w-12 text-right shrink-0 pt-0.5">
                  <span className="text-[10px] font-mono tracking-wider text-[#9CA3AF]">
                    {item.time}
                  </span>
                </div>
                
                {/* Node */}
                <div className="relative flex flex-col items-center">
                  <div 
                    className={`w-3 h-3 rounded-full mt-1.5 outline outline-4 outline-[#FEEFE1] ${
                      item.current ? "bg-[#111111]" : "bg-[#B8B8B8]"
                    }`} 
                  />
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
              </m.div>
            </StaggerItem>
          ))}
        </StaggerContainer>
      </div>
    </div>
  );
}
