"use client";

import { useEffect, useState, ReactNode } from "react";

interface AdLayoutProps {
  children: ReactNode;
}

export default function AdLayout({ children }: AdLayoutProps) {
  const [adsEnabled, setAdsEnabled] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const enabled = process.env.NEXT_PUBLIC_ADS_ENABLED === "true";
    setAdsEnabled(enabled);
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div className="w-full h-full min-h-0 flex-1">
        {children}
      </div>
    );
  }

  if (!adsEnabled) {
    return (
      <div className="w-full h-full min-h-0 flex-1 transition-all duration-500 ease-in-out">
        {children}
      </div>
    );
  }

  return (
    <div className="w-full h-full min-h-0 flex-1 flex flex-col lg:flex-row gap-6 transition-all duration-500 ease-in-out max-w-[1800px] mx-auto px-4 sm:px-5">
      {/* Main Content Area */}
      <div className="flex-1 h-full min-h-0 min-w-0 transition-all duration-500 ease-in-out">
        {children}
      </div>

      {/* Reusable Advertisement Column */}
      <aside className="w-full lg:w-[300px] h-full shrink-0 transition-all duration-500 ease-in-out hidden lg:block overflow-y-auto scrollbar-thin border-l border-[#1a1a1a] bg-[#090909]/40">
        <div className="p-4 space-y-4">
          <div className="border border-[#1a1a1a] bg-[#0c0c0c] p-4 flex flex-col items-center justify-center min-h-[450px] relative overflow-hidden select-none">
            {/* Ambient cyber grid in background */}
            <div className="absolute inset-0 opacity-[0.02] bg-[linear-gradient(to_right,#808080_1px,transparent_1px),linear-gradient(to_bottom,#808080_1px,transparent_1px)] bg-[size:14px_24px]" />
            
            {/* Header label */}
            <div className="font-mono text-[8px] tracking-[0.2em] text-[#555] uppercase mb-4 border-b border-[#1a1a1a] w-full text-center pb-2 z-10">
              Sponsored Transmission
            </div>

            {/* Core Ad Slots */}
            <div className="w-full space-y-4 z-10">
              <div className="border border-[#1f1f1f] bg-[#080808] h-[180px] w-full flex flex-col items-center justify-center p-3 relative group hover:border-[#333] transition-colors">
                <div className="absolute top-0 right-0 border-l border-b border-[#1f1f1f] bg-[#080808] px-1 py-0.5 font-mono text-[5px] tracking-widest text-[#555]">
                  NODE_A
                </div>
                <div className="font-mono text-[9px] text-[#444] tracking-widest uppercase mb-1">
                  Advertisement
                </div>
                <div className="text-center font-sans text-[10px] text-neutral-500 px-2 line-clamp-3">
                  Autonomous Intelligence Solutions. Streamline your operational indexing.
                </div>
                <div className="mt-3 font-mono text-[7px] text-[#3b82f6] uppercase tracking-wider group-hover:underline cursor-pointer">
                  Query System Node ↗
                </div>
              </div>

              <div className="border border-[#1f1f1f] bg-[#080808] h-[180px] w-full flex flex-col items-center justify-center p-3 relative group hover:border-[#333] transition-colors">
                <div className="absolute top-0 right-0 border-l border-b border-[#1f1f1f] bg-[#080808] px-1 py-0.5 font-mono text-[5px] tracking-widest text-[#555]">
                  NODE_B
                </div>
                <div className="font-mono text-[9px] text-[#444] tracking-widest uppercase mb-1">
                  Ad Slot Placeholder
                </div>
                <div className="text-center font-sans text-[10px] text-neutral-500 px-2 line-clamp-3">
                  Monetize premium editorial feeds dynamically without layout refresh.
                </div>
                <div className="mt-3 font-mono text-[7px] text-neutral-400 uppercase tracking-wider">
                  Partner Placements
                </div>
              </div>
            </div>

            {/* Footer label */}
            <div className="font-mono text-[7px] text-[#444] uppercase tracking-widest mt-4 z-10">
              MONITOR ID: TNT-AD-SYS
            </div>
          </div>
        </div>
      </aside>
    </div>
  );
}
