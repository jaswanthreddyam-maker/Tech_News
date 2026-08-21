"use client";

import React, { useState, useMemo, useRef, useEffect } from "react";
import { useCategoryDesks } from "@/components/hooks/articles/useArticles";
import { 
  Sparkles, 
  Link as LinkIcon,
  ShieldCheck, 
  Cloud,
  TrendingUp,
  Infinity as InfinityIcon,
  Atom, 
  Globe,
  LayoutGrid,
  Smartphone,
  Cpu, 
  Rocket, 
  Scale, 
  Layers, 
  ChevronDown,
  Newspaper,
  LucideIcon
} from "lucide-react";
import { EmptyState, EmptyIllustration } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { m, AnimatePresence, useScroll, useTransform } from "framer-motion";
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

/** Icon resolver based on category slug keywords */
function getCategoryIcon(slug: string): LucideIcon {
  const s = slug.toLowerCase();
  if (s.includes("ai") || s.includes("artificial-intelligence") || s.includes("intelligence") || s.includes("machine-learning")) return Sparkles;
  if (s.includes("blockchain") || s.includes("crypto")) return LinkIcon;
  if (s.includes("cyber") || s.includes("security") || s.includes("privacy")) return ShieldCheck;
  if (s.includes("cloud")) return Cloud;
  if (s.includes("data") || s.includes("analytics")) return TrendingUp;
  if (s.includes("devops") || s.includes("infra") || s.includes("ci-cd")) return InfinityIcon;
  if (s.includes("quantum") || s.includes("science") || s.includes("physics")) return Atom;
  if (s.includes("web3") || s.includes("defi")) return Globe;
  if (s.includes("robot") || s.includes("automation")) return Cpu;
  if (s.includes("hardware") || s.includes("device") || s.includes("chip") || s.includes("semiconductor")) return Smartphone;
  if (s.includes("startup") || s.includes("business") || s.includes("venture")) return Rocket;
  if (s.includes("policy") || s.includes("govern") || s.includes("legal") || s.includes("ethics")) return Scale;
  return Layers;
}

/** Curated metadata dictionary for known desks */
const KNOWN_METADATA: Record<string, Omit<CategoryMeta, "key">> = {
  "artificial-intelligence": {
    title: "Artificial Intelligence",
    icon: Sparkles,
    tags: "LLMs • Neural Systems • AI Research",
    order: 1,
  },
  "cybersecurity": {
    title: "Cybersecurity",
    icon: ShieldCheck,
    tags: "Security Research • Encryption • Defense",
    order: 2,
  },
  "hardware": {
    title: "Hardware & Devices",
    icon: Smartphone,
    tags: "Semiconductors • Chips • Devices",
    order: 3,
  },
  "robotics": {
    title: "Robotics",
    icon: Cpu,
    tags: "Humanoids • Autonomous Systems • Drones",
    order: 4,
  },
  "science": {
    title: "Science & Quantum",
    icon: Atom,
    tags: "Quantum Computing • Physics • Biotech",
    order: 5,
  },
  "startups-and-business": {
    title: "Startups & Business",
    icon: Rocket,
    tags: "Venture Capital • Funding • Innovation",
    order: 6,
  },
  "policy": {
    title: "Policy & Governance",
    icon: Scale,
    tags: "AI Governance • Tech Law • Ethics",
    order: 7,
  },
  "technology": {
    title: "General Technology",
    icon: Layers,
    tags: "Software • Applications • Ecosystems",
    order: 8,
  },
  "blockchain": {
    title: "Blockchain",
    icon: LinkIcon,
    tags: "Decentralized Systems • Smart Contracts • Protocols",
    order: 9,
  },
  "cloud-computing": {
    title: "Cloud Computing",
    icon: Cloud,
    tags: "Cloud Infrastructure • Serverless • Microservices",
    order: 10,
  },
  "data-science": {
    title: "Data Science",
    icon: TrendingUp,
    tags: "Big Data • Analytics • Predictive Modeling",
    order: 11,
  },
  "devops": {
    title: "DevOps",
    icon: InfinityIcon,
    tags: "CI/CD • Kubernetes • Automation • Infrastructure",
    order: 12,
  },
  "quantum-computing": {
    title: "Quantum Computing",
    icon: Atom,
    tags: "Quantum Algorithms • Qubits • Supercomputing",
    order: 13,
  },
  "web3": {
    title: "Web3",
    icon: Globe,
    tags: "Decentralized Web • DeFi • Digital Assets",
    order: 14,
  },
};

export function LatestNews() {
  const { data: categoryGroups, isLoading, error } = useCategoryDesks();
  const { scrollYProgress } = useScroll();
  const [selectedKey, setSelectedKey] = useState<string>("");
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click or escape
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsDropdownOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  // Subtle Scroll Parallax Depth
  const sectionBgY = useTransform(scrollYProgress, [0, 1], [0, 40]);
  const contentY = useTransform(scrollYProgress, [0, 1], [0, 15]);

  // Dynamically compute only categories that actually have fetched articles
  const availableCategories = useMemo(() => {
    if (!categoryGroups || !Array.isArray(categoryGroups)) return [];

    return categoryGroups
      .filter((desk: any) => desk && Array.isArray(desk.articles) && desk.articles.length > 0)
      .map((desk: any) => {
        const slug = (desk.slug || "").toLowerCase().trim();
        const known = KNOWN_METADATA[slug];

        const title = known?.title || desk.headline || slug.replace(/-/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase());
        const icon = known?.icon || getCategoryIcon(slug);
        const tags = known?.tags || `${desk.headline || title} • Featured Stories`;
        const order = known?.order ?? (desk.display_order || 99);

        return {
          key: slug,
          title,
          icon,
          tags,
          order,
          articlesCount: desk.articles.length,
          desk,
        };
      })
      .sort((a, b) => a.order - b.order);
  }, [categoryGroups]);

  // Ensure selectedKey is always set to an existing category
  useEffect(() => {
    if (availableCategories.length > 0) {
      const exists = availableCategories.some((c) => c.key === selectedKey);
      if (!exists) {
        setSelectedKey(availableCategories[0].key);
      }
    }
  }, [availableCategories, selectedKey]);

  // Active Category & Articles
  const activeCategory = useMemo(() => {
    if (availableCategories.length === 0) return null;
    return availableCategories.find((c) => c.key === selectedKey) || availableCategories[0];
  }, [availableCategories, selectedKey]);

  const displayArticles = useMemo(() => {
    return activeCategory?.desk?.articles?.slice(0, 4) || [];
  }, [activeCategory]);

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

  if (!availableCategories || availableCategories.length === 0) return (
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

  const CurrentIcon = activeCategory?.icon || Sparkles;

  return (
    <MotionDirector cameraMultiplier={0.15}>
      <m.section 
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.01 }}
        transition={{ duration: 0.6, ease: EASE_CUBIC }}
        className="py-12 sm:py-20 border border-white/10 mt-12 mb-24 relative rounded-3xl overflow-hidden bg-black/30 backdrop-blur-md p-4 sm:p-8 lg:p-10 shadow-2xl"
      >
        {/* Layer 1: Spatial Volume Environment with Parallax */}
        <m.div style={{ y: sectionBgY }} className="absolute inset-0 pointer-events-none z-0 overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808008_1px,transparent_1px),linear-gradient(to_bottom,#80808008_1px,transparent_1px)] bg-[size:40px_40px] opacity-30" />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_30%,rgba(0,0,0,0.6)_100%)] opacity-70" />
        </m.div>

        <m.div style={{ y: contentY }} className="relative z-10 w-full">

          {/* Section Header with Category Chooser */}
          <m.div 
            initial={{ opacity: 0, y: 15 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.01 }}
            transition={{ duration: 0.5, delay: 0.0, ease: EASE_CUBIC }}
            className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-10"
          >
            <div>
              <h2 className="text-xl sm:text-2xl font-sans font-bold tracking-tight text-foreground">
                Browse by Category
              </h2>
            </div>

            {/* Choose Category Dropdown */}
            <div className="relative" ref={dropdownRef}>
              <div className="text-xs text-muted-foreground/80 mb-1.5 font-medium">
                Choose Category
              </div>
              <button
                type="button"
                id="choose-category-dropdown"
                onClick={() => setIsDropdownOpen((prev) => !prev)}
                className="flex items-center justify-between gap-3 min-w-[220px] px-4 py-2.5 rounded-xl bg-[#0e0f12]/90 hover:bg-[#16181d] border border-white/10 hover:border-white/20 text-sm font-medium text-foreground transition-all duration-200 shadow-lg cursor-pointer focus:outline-none focus:ring-1 focus:ring-primary/40"
                aria-haspopup="listbox"
                aria-expanded={isDropdownOpen}
              >
                <span>{activeCategory?.title || "Select Category"}</span>
                <ChevronDown 
                  className={`w-4 h-4 text-muted-foreground transition-transform duration-200 ${
                    isDropdownOpen ? "rotate-180 text-foreground" : ""
                  }`} 
                />
              </button>

              {/* Dropdown Menu Box */}
              <AnimatePresence>
                {isDropdownOpen && (
                  <m.div
                    initial={{ opacity: 0, y: -6, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -6, scale: 0.98 }}
                    transition={{ duration: 0.15, ease: "easeOut" }}
                    className="absolute right-0 mt-2 w-[240px] py-2 rounded-2xl bg-[#0c0d10]/95 backdrop-blur-xl border border-white/10 shadow-2xl z-50 overflow-hidden max-h-[380px] overflow-y-auto"
                    role="listbox"
                  >
                    {availableCategories.map((cat) => {
                      const isSelected = activeCategory?.key === cat.key;
                      const CatIcon = cat.icon;
                      return (
                        <button
                          key={cat.key}
                          type="button"
                          role="option"
                          aria-selected={isSelected}
                          onClick={() => {
                            setSelectedKey(cat.key);
                            setIsDropdownOpen(false);
                          }}
                          className={`w-full flex items-center gap-3 px-4 py-2.5 text-sm font-medium transition-colors relative text-left cursor-pointer ${
                            isSelected
                              ? "text-[#ff6b2b] bg-white/[0.04]"
                              : "text-zinc-300 hover:text-white hover:bg-white/[0.04]"
                          }`}
                        >
                          {/* Active Indicator Line */}
                          {isSelected && (
                            <span className="absolute left-0 top-1.5 bottom-1.5 w-1 bg-[#ff6b2b] rounded-r-full" />
                          )}
                          <CatIcon 
                            className={`w-4 h-4 shrink-0 ${isSelected ? "text-[#ff6b2b]" : "text-zinc-400"}`} 
                            strokeWidth={1.75} 
                          />
                          <span className="truncate">{cat.title}</span>
                        </button>
                      );
                    })}
                  </m.div>
                )}
              </AnimatePresence>
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

            {/* Selected Category Desk Presentation */}
            <AnimatePresence mode="wait">
              {activeCategory && (
                <m.div
                  key={activeCategory.key}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -12 }}
                  transition={{ duration: 0.35, ease: EASE_CUBIC }}
                  className="w-full space-y-10"
                >
                  {/* Category Header Row */}
                  <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 pb-4 border-b border-white/10">
                    <div className="space-y-1.5">
                      <div className="flex items-center gap-2.5">
                        <CurrentIcon className="w-5 h-5 text-foreground shrink-0" strokeWidth={1.75} />
                        <h3 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground font-sans">
                          {activeCategory.title}
                        </h3>
                      </div>

                      <div className="text-xs font-mono text-muted-foreground/60">
                        {activeCategory.tags}
                      </div>
                    </div>
                  </div>

                  {/* Asymmetric Magazine/Editorial Grid */}
                  {displayArticles.length > 0 ? (
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
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.5, delay: i * 0.05, ease: EASE_CUBIC }}
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
                  ) : (
                    <div className="py-16 text-center text-muted-foreground text-sm font-mono bg-white/[0.02] rounded-2xl border border-white/5">
                      No articles found for {activeCategory.title} at this moment.
                    </div>
                  )}
                </m.div>
              )}
            </AnimatePresence>
          </Scene3DProvider>

        </m.div>
      </m.section>
    </MotionDirector>
  );
}


