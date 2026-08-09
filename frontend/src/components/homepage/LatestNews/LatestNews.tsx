"use client";

import React, { useMemo } from "react";
import Link from "next/link";
import { useCategoryDesks } from "@/components/hooks/articles/useArticles";
import { 
  Cpu, 
  Sparkles, 
  Rocket, 
  ShieldCheck, 
  Smartphone, 
  Atom, 
  TrendingUp, 
  Scale, 
  Layers, 
  ArrowRight, 
  Newspaper,
  LucideIcon
} from "lucide-react";
import { EmptyState, EmptyIllustration } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { m, useScroll, useTransform } from "framer-motion";
import { Scene3DProvider } from "@/components/common/Scene3DProvider";
import { FloatingEditorialPanel } from "./FloatingEditorialPanel";
import { MotionDirector } from "@/components/animations/MotionDirector";
import { MOTION_TOKENS } from "@/components/animations/motionTokens";
import { EditorialCardSkeleton } from "@/components/skeletons/EditorialCardSkeleton";

/** Apple / Arc Signature Easing Curve */
const EASE_CUBIC = [0.16, 1, 0.3, 1] as const;

interface CategoryMeta {
  key: string;
  title: string;
  icon: LucideIcon;
  tags: string;
  order: number;
}

/** Category Metadata & Priority Order Specification */
const CATEGORY_METADATA: Record<string, CategoryMeta> = {
  "artificial-intelligence": {
    key: "artificial-intelligence",
    title: "Artificial Intelligence",
    icon: Sparkles,
    tags: "LLMs • Neural Systems • AI Research",
    order: 1,
  },
  cybersecurity: {
    key: "cybersecurity",
    title: "Cybersecurity",
    icon: ShieldCheck,
    tags: "Security Research • Encryption • Defense",
    order: 2,
  },
  hardware: {
    key: "hardware",
    title: "Hardware & Devices",
    icon: Smartphone,
    tags: "Semiconductors • Chips • Devices",
    order: 3,
  },
  robotics: {
    key: "robotics",
    title: "Robotics",
    icon: Cpu,
    tags: "Humanoids • Autonomous Systems • Drones",
    order: 4,
  },
  science: {
    key: "science",
    title: "Science & Quantum",
    icon: Atom,
    tags: "Quantum Computing • Physics • Biotech",
    order: 5,
  },
  "startups-and-business": {
    key: "startups-and-business",
    title: "Startups & Business",
    icon: Rocket,
    tags: "Venture Capital • Funding • Innovation",
    order: 6,
  },
  policy: {
    key: "policy",
    title: "Policy & Governance",
    icon: Scale,
    tags: "AI Governance • Tech Law • Ethics",
    order: 7,
  },
  technology: {
    key: "technology",
    title: "General Technology",
    icon: Layers,
    tags: "Software • Applications • Ecosystems",
    order: 8,
  },
};

export function LatestNews() {
  const { data: categoryGroups, isLoading, error } = useCategoryDesks();
  const { scrollYProgress } = useScroll();

  // Subtle Scroll Parallax Depth
  const sectionBgY = useTransform(scrollYProgress, [0, 1], [0, 40]);
  const contentY = useTransform(scrollYProgress, [0, 1], [0, 15]);

  if (isLoading) {
    return (
      <section className="py-12 border-t border-border/20 mt-8 min-h-[400px] relative rounded-3xl overflow-hidden bg-gradient-to-b from-[#0e0f12]/40 via-background to-background p-4 sm:p-8 lg:p-10">
        <div className="flex items-center gap-3 mb-10">
          <div className="p-2 bg-primary/10 rounded-lg border border-primary/20">
            <Layers className="w-5 h-5 text-primary" strokeWidth={1.5} />
          </div>
          <div>
            <h2 className="text-2xl sm:text-3xl font-sans font-bold tracking-tight text-foreground">Explore by Category</h2>
            <p className="text-xs font-mono text-muted-foreground/70 mt-0.5">Discover the latest stories organized by topic.</p>
          </div>
        </div>

        <div className="space-y-12 w-full">
          {[...Array(2)].map((_, catIdx) => (
            <div key={catIdx} className="space-y-6">
              <div className="pb-4 border-b border-white/10 flex justify-between items-end">
                <div className="space-y-2">
                  <div className="h-7 w-48 bg-white/5 rounded-md animate-pulse" />
                  <div className="h-3.5 w-72 bg-white/5 rounded animate-pulse" />
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 w-full">
                <EditorialCardSkeleton />
                <EditorialCardSkeleton />
                <EditorialCardSkeleton />
                <EditorialCardSkeleton />
              </div>
            </div>
          ))}
        </div>
      </section>
    );
  }

  if (error) return (
    <div className="py-8 mt-8">
      <ErrorState title="Error loading news" description="Could not load the category feed." />
    </div>
  );

  if (!categoryGroups || categoryGroups.length === 0) return (
    <div className="py-8 mt-8">
      <EmptyState>
        <EmptyIllustration
          icon={Newspaper}
          title="No stories available"
          description="Check back in a few minutes."
        />
      </EmptyState>
    </div>
  );

  return (
    <MotionDirector cameraMultiplier={0.15}>
      <m.section 
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.01 }}
        transition={{ duration: 0.6, ease: EASE_CUBIC }}
        className="py-12 sm:py-20 border-t border-border/20 mt-12 mb-24 relative rounded-3xl overflow-hidden bg-gradient-to-b from-[#0e0f12]/40 via-background to-background p-4 sm:p-8 lg:p-10"
      >
        {/* Layer 1: Spatial Volume Environment with Parallax */}
        <m.div style={{ y: sectionBgY }} className="absolute inset-0 pointer-events-none z-0 overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808008_1px,transparent_1px),linear-gradient(to_bottom,#80808008_1px,transparent_1px)] bg-[size:40px_40px] opacity-40" />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_30%,rgba(0,0,0,0.85)_100%)] opacity-70" />
        </m.div>

        <m.div style={{ y: contentY }} className="relative z-10 w-full">


          <m.div 
            initial={{ opacity: 0, y: 15 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.01 }}
            transition={{ duration: 0.5, delay: 0.0, ease: EASE_CUBIC }}
            className="space-y-4 mb-12"
          >
            <div className="flex items-center justify-between mb-8">
              <h2 className="text-xl sm:text-2xl font-sans font-bold tracking-tight text-foreground">
                Browse by Category
              </h2>
            </div>
          </m.div>

          <Scene3DProvider className="w-full relative z-10" cameraMaxRotateX={0.3} cameraMaxRotateY={0.3}>
            {/* Layer 2: Neutral Ambient Lighting */}
            <m.div
              className="absolute pointer-events-none rounded-full bg-white/[0.04] blur-[180px] mix-blend-screen z-0"
              style={{
                width: 1100,
                height: 1100,
                left: 'calc(var(--light-x, 50%) - 550px)',
                top: 'calc(var(--light-y, 50%) - 550px)',
                transition: 'left 1s cubic-bezier(0.2,0.8,0.2,1), top 1s cubic-bezier(0.2,0.8,0.2,1)',
              }}
              initial={{ opacity: 0 }}
              whileInView={{ opacity: [0.05, 0.08, 0.05] }}
              transition={{ duration: MOTION_TOKENS.IDLE_BREATHING_DESK, repeat: Infinity, ease: MOTION_TOKENS.EASING_IDLE }}
              viewport={{ once: true }}
            />

            {/* Sequenced Category Desks Grid */}
            <div className="space-y-32 w-full relative z-10">
              {categoryGroups.map((desk: any) => {
                const displayArticles = desk.articles.slice(0, 4);
                if (displayArticles.length === 0) return null;
                const meta = CATEGORY_METADATA[desk.slug.toLowerCase()] || { icon: Layers, tags: "Featured Category" };
                const IconComponent = meta.icon || Layers;

                return (
                  <m.section
                    key={desk.slug}
                    aria-labelledby={`category-title-${desk.slug}`}
                    initial={{ opacity: 0, y: 15 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, amount: 0.01 }}
                    transition={{ duration: 0.6, ease: EASE_CUBIC }}
                    className="w-full space-y-12"
                  >
                    {/* Category Header Row */}
                    <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 pb-4 border-b border-white/10">
                      <div className="space-y-1.5">
                        <div className="flex items-center gap-2.5">
                          <IconComponent className="w-4.5 h-4.5 text-muted-foreground/70 shrink-0" strokeWidth={1.5} />
                          <h3
                            id={`category-title-${desk.slug}`}
                            className="text-xl sm:text-2xl font-bold tracking-tight text-foreground font-sans"
                          >
                            {desk.headline}
                          </h3>
                        </div>

                        <div className="text-xs font-mono text-muted-foreground/60">
                          {meta.tags}
                        </div>
                      </div>
                    </div>

                    {/* Asymmetric Magazine/Editorial Grid */}
                    <div 
                      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 lg:gap-8 w-full items-stretch"
                      style={{ 
                        transformStyle: "preserve-3d",
                        transform: "rotateX(calc(var(--camera-rotate-x, 0))) rotateY(calc(var(--camera-rotate-y, 0)))",
                      }}
                    >
                      {displayArticles.map((article: any, i: number) => {
                        const isPrimary = i === 0;
                        let spanClass = "col-span-1";
                        if (i === 0) spanClass = "sm:col-span-2 lg:col-span-2 lg:row-span-2";
                        if (i === 3) spanClass = "sm:col-span-2 lg:col-span-2 lg:row-span-1";
                        
                        return (
                          <m.div
                            key={article.id || i}
                            initial={{ opacity: 0, y: 24 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true, amount: 0.15 }}
                            transition={{ duration: 0.7, delay: 0.15 + i * 0.07, ease: EASE_CUBIC }}
                            className={`w-full h-full ${spanClass}`}
                          >
                            <FloatingEditorialPanel
                              article={article}
                              index={i}
                              isPrimary={isPrimary}
                            />
                          </m.div>
                        );
                      })}
                    </div>
                  </m.section>
                );
              })}
            </div>
          </Scene3DProvider>

        </m.div>
      </m.section>
    </MotionDirector>
  );
}
