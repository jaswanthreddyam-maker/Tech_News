"use client";

import { Reveal, StaggerContainer, StaggerItem } from "@/components/animations";
import { m } from "framer-motion";
import { MotionScales } from "@/design-system/motion/tokens";
import { useState, useEffect } from "react";
import { Skeleton } from "@/design-system/components/Skeleton";
import { useLoadingState } from "@/design-system/hooks/useLoadingState";

/* eslint-disable react/jsx-no-comment-textnodes, @typescript-eslint/no-unused-vars */
export interface TimelineItem {
  id: string | number;
  time: string;
  label: string;
  source: string;
  current?: boolean;
}

interface StoryEvolutionProps {
  items?: TimelineItem[];
}

export function StoryEvolution({ items }: StoryEvolutionProps) {
  const [timelineItems, setTimelineItems] = useState<TimelineItem[]>(items || []);
  const [loading, setLoading] = useState(!items);

  useEffect(() => {
    if (items) {
      setTimelineItems(items);
      setLoading(false);
      return;
    }

    async function fetchStories() {
      try {
        const { apiClient } = await import("@/lib/api/client");
        const res = await apiClient.fetchJson<any[]>("/stories?limit=5");
        if (Array.isArray(res) && res.length > 0) {
          const mapped: TimelineItem[] = res.map((story: any, idx: number) => ({
            id: story.id,
            time: story.created_at ? new Date(story.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "Live",
            label: story.title,
            source: story.created_by || "AI Synthesized",
            current: idx === 0,
          }));
          setTimelineItems(mapped);
        }
      } catch (err) {
        // Silently handle if no active stories exist
      } finally {
        setLoading(false);
      }
    }

    fetchStories();
  }, [items]);

  if (loading || timelineItems.length === 0) {
    return null;
  }

  return (
    <div className="py-8 border-t border-border mt-8">
      <Reveal>
        <h2 className="text-2xl font-sans font-bold tracking-tight mb-6 text-[#111827] dark:text-white">Story Evolution</h2>
      </Reveal>
      <m.div 
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: "-100px" }}
        variants={{
          hidden: { clipPath: "circle(30px at center)" },
          visible: { 
            clipPath: "circle(150% at center)", 
            transition: { duration: 2.0, ease: [0.22, 1, 0.36, 1] } 
          }
        }}
        className="py-8 border rounded-[24px] relative"
        style={{
          background: "linear-gradient(180deg, #FFF5EC 0%, #FEEFE1 100%)",
          borderColor: "#E9D8C7",
          boxShadow: "0 10px 30px rgba(0,0,0,0.05)",
          paddingLeft: "48px",
          paddingRight: "48px"
        }}
      >
        <m.div
          variants={{
            hidden: { opacity: 0 },
            visible: { opacity: 1, transition: { delay: 1.2, duration: 0.8, ease: "easeOut" } }
          }}
        >
          <div className="absolute left-[126px] top-10 bottom-10 w-px" style={{ backgroundColor: "rgba(0,0,0,0.08)" }} />
          
          <StaggerContainer className="space-y-8 relative z-10">
          {timelineItems.map((item) => (
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
        </m.div>
      </m.div>
    </div>
  );
}
