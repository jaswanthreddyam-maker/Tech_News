"use client";

import React from "react";
import Link from "next/link";
import { Cpu, Bot, Rocket, Shield, Code2, Globe2, Sparkles, Star, ArrowRight, Cloud, Coins, BookOpen } from "lucide-react";
import { m } from "framer-motion";
import { Article } from "@/lib/api/types";
import { useFollowTopic } from "@/hooks/useFollow";
import { useAppStore } from "@/store/useStore";
import { useState, useEffect } from "react";

export interface Topic {
  id: number;
  name: string;
  slug: string;
  articles: Article[];
  totalCount: number;
  lastUpdated: string | null;
  description?: string;
  progress?: number;
}

interface TopicCardProps {
  topic: Topic;
  viewMode?: "grid" | "list";
}

const CATEGORY_THEMES: Record<string, { icon: any; colorClass: string; textClass: string; bgClass: string; borderClass: string; progress: number; description: string }> = {
  "artificial-intelligence": {
    icon: Cpu,
    colorClass: "from-neutral-950/20 to-neutral-950/5 dark:from-white/10 dark:to-white/5",
    textClass: "text-neutral-950 dark:text-white",
    bgClass: "bg-neutral-950/5 dark:bg-white/5",
    borderClass: "hover:border-neutral-950/30 dark:hover:border-white/20",
    progress: 86,
    description: "Latest breakthroughs in AI research, foundation models, and applied intelligence.",
  },
  "robotics": {
    icon: Bot,
    colorClass: "from-rose-500/20 to-orange-500/5 dark:from-rose-500/30 dark:to-orange-500/10",
    textClass: "text-rose-500 dark:text-rose-400",
    bgClass: "bg-rose-500/5",
    borderClass: "hover:border-rose-500/30",
    progress: 12,
    description: "Advancements in robotics, hardware automation, mechanics, and intelligent systems.",
  },
  "startups": {
    icon: Rocket,
    colorClass: "from-emerald-500/20 to-teal-500/5 dark:from-emerald-500/30 dark:to-teal-500/10",
    textClass: "text-emerald-500 dark:text-emerald-400",
    bgClass: "bg-emerald-500/5",
    borderClass: "hover:border-emerald-500/30",
    progress: 16,
    description: "Funding news, tech startup ecosystems, venture capital, and emerging disruptors.",
  },
  "cybersecurity": {
    icon: Shield,
    colorClass: "from-amber-500/20 to-red-500/5 dark:from-amber-500/30 dark:to-red-500/10",
    textClass: "text-amber-500 dark:text-amber-400",
    bgClass: "bg-amber-500/5",
    borderClass: "hover:border-amber-500/30",
    progress: 48,
    description: "Security vulnerabilities, data privacy, threat intelligence, and digital defense systems.",
  },
  "software-development": {
    icon: Code2,
    colorClass: "from-blue-500/20 to-cyan-500/5 dark:from-blue-500/30 dark:to-cyan-500/10",
    textClass: "text-blue-500 dark:text-blue-400",
    bgClass: "bg-blue-500/5",
    borderClass: "hover:border-blue-500/30",
    progress: 64,
    description: "Modern languages, developer tools, web frameworks, DevOps, and cloud deployment.",
  },
  "space-science": {
    icon: Globe2,
    colorClass: "from-neutral-950/20 to-neutral-950/5 dark:from-white/10 dark:to-white/5",
    textClass: "text-neutral-950 dark:text-white",
    bgClass: "bg-neutral-950/5 dark:bg-white/5",
    borderClass: "hover:border-neutral-950/30 dark:hover:border-white/20",
    progress: 35,
    description: "Aerospace engineering, space exploration milestones, astronomy, and satellite tech.",
  },
  "semiconductors": {
    icon: Cpu,
    colorClass: "from-cyan-500/20 to-teal-500/5 dark:from-cyan-500/30 dark:to-teal-500/10",
    textClass: "text-cyan-500 dark:text-cyan-400",
    bgClass: "bg-cyan-500/5",
    borderClass: "hover:border-cyan-500/30",
    progress: 9,
    description: "Microchip manufacturing, processor architectures, lithography, and global supply chains.",
  },
  "cloud-computing": {
    icon: Cloud,
    colorClass: "from-sky-500/20 to-blue-500/5 dark:from-sky-500/30 dark:to-blue-500/10",
    textClass: "text-sky-500 dark:text-sky-400",
    bgClass: "bg-sky-500/5",
    borderClass: "hover:border-sky-500/30",
    progress: 27,
    description: "Serverless architectures, hyper-scale cloud vendors, databases, and edge nodes.",
  },
  "fintech": {
    icon: Coins,
    colorClass: "from-yellow-500/20 to-amber-500/5 dark:from-yellow-500/30 dark:to-yellow-500/10",
    textClass: "text-yellow-500 dark:text-yellow-400",
    bgClass: "bg-yellow-500/5",
    borderClass: "hover:border-yellow-500/30",
    progress: 18,
    description: "Digital banking, blockchain infrastructure, micro-transactions, and trading systems.",
  },
  "general": {
    icon: Sparkles,
    colorClass: "from-neutral-500/20 to-neutral-500/5 dark:from-neutral-500/30 dark:to-neutral-500/10",
    textClass: "text-neutral-500 dark:text-neutral-400",
    bgClass: "bg-neutral-500/5",
    borderClass: "hover:border-neutral-500/30",
    progress: 5,
    description: "General tech announcements, consumer electronics, and technology industry news.",
  },
};

export function useTopicFavorite(topicName: string) {
  const { user } = useAppStore();
  const apiFollow = useFollowTopic(topicName);
  const [localFollow, setLocalFollow] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    if (!user && typeof window !== "undefined") {
      const stored = localStorage.getItem("followed_topics");
      if (stored) {
        try {
          const list = JSON.parse(stored);
          setLocalFollow(list.includes(topicName));
        } catch (e) {
          console.error(e);
        }
      }
    }
  }, [user, topicName]);

  const isFav = user ? apiFollow.isFollowing : localFollow;

  const toggleFav = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    if (user) {
      await apiFollow.toggleFollow();
    } else if (typeof window !== "undefined") {
      const stored = localStorage.getItem("followed_topics");
      let list = stored ? JSON.parse(stored) : [];
      if (list.includes(topicName)) {
        list = list.filter((t: string) => t !== topicName);
        setLocalFollow(false);
      } else {
        list.push(topicName);
        setLocalFollow(true);
      }
      localStorage.setItem("followed_topics", JSON.stringify(list));
    }
  };

  return { isFav, toggleFav, isLoading: user ? apiFollow.isLoading : false, mounted };
}

export function TopicCard({ topic, viewMode = "grid" }: TopicCardProps) {
  const theme = CATEGORY_THEMES[topic.slug] || {
    icon: Sparkles,
    colorClass: "from-neutral-500/20 to-neutral-500/5 dark:from-neutral-500/30 dark:to-neutral-500/10",
    textClass: "text-neutral-500 dark:text-neutral-400",
    bgClass: "bg-neutral-500/5",
    borderClass: "hover:border-neutral-500/30",
    progress: Math.max(5, (topic.totalCount * 7) % 100),
    description: "Tech category covering real-time developments, analysis, and news coverage.",
  };

  const IconComponent = theme.icon;
  const description = topic.description || theme.description;
  const progressVal = topic.progress !== undefined ? topic.progress : theme.progress;
  const { isFav, toggleFav, mounted } = useTopicFavorite(topic.name);

  const getProgressColor = (slug: string) => {
    if (slug.includes("ai") || slug.includes("intelligence")) return "bg-neutral-950 dark:bg-white";
    if (slug.includes("robot")) return "bg-rose-500";
    if (slug.includes("startup")) return "bg-emerald-500";
    if (slug.includes("cyber") || slug.includes("security")) return "bg-amber-500";
    if (slug.includes("dev") || slug.includes("software")) return "bg-blue-500";
    if (slug.includes("space") || slug.includes("science")) return "bg-neutral-950 dark:bg-white";
    if (slug.includes("semi")) return "bg-cyan-500";
    if (slug.includes("cloud")) return "bg-sky-500";
    if (slug.includes("fin")) return "bg-yellow-500";
    return "bg-neutral-500 dark:bg-neutral-400";
  };

  if (viewMode === "list") {
    return (
      <m.div
        whileHover={{ y: -4 }}
        transition={{ type: "spring", stiffness: 300, damping: 20 }}
        className="rounded-xl border border-border bg-card/65 dark:bg-card/40 hover:bg-card/90 dark:hover:bg-card/75 text-card-foreground p-5 shadow-sm hover:shadow-md hover:border-black/20 dark:hover:border-white/20 hover:shadow-black/10 dark:hover:shadow-white/10 transition-all flex flex-col md:flex-row items-start md:items-center gap-6 justify-between focus-within:ring-2 focus-within:ring-neutral-950 dark:focus-within:ring-white/50 outline-none select-none relative"
      >
        <div className="flex items-start gap-4 flex-1">
          <div className={`p-3.5 rounded-xl bg-gradient-to-br ${theme.colorClass} ${theme.textClass} shrink-0`}>
            <IconComponent className="w-6 h-6" />
          </div>

          <div className="space-y-1.5 flex-1 min-w-0">
            <div className="flex items-center gap-3">
              <h3 className="text-lg font-bold tracking-tight text-foreground line-clamp-1">
                {topic.name}
              </h3>
              <button
                onClick={toggleFav}
                className="text-muted-foreground/40 hover:text-yellow-500 transition-colors p-1"
                aria-label={isFav ? `Unfavorite ${topic.name}` : `Favorite ${topic.name}`}
              >
                <Star
                  className={`w-4 h-4 transition-all duration-300 ${
                    mounted && isFav ? "fill-yellow-500 text-yellow-500 scale-110" : "text-muted-foreground/60 hover:scale-105"
                  }`}
                />
              </button>
            </div>

            <div className="flex flex-wrap items-center gap-2.5 text-xs font-mono text-muted-foreground/60">
              <span className="flex items-center gap-1">
                <BookOpen className="w-3.5 h-3.5" />
                {topic.totalCount} {topic.totalCount === 1 ? "Article" : "Articles"}
              </span>
              {topic.lastUpdated && (
                <>
                  <span className="w-1 h-1 rounded-full bg-border"></span>
                  <span>Updated {topic.lastUpdated}</span>
                </>
              )}
            </div>

            <p className="text-sm text-muted-foreground/75 leading-relaxed line-clamp-2">
              {description}
            </p>
          </div>
        </div>

        <div className="w-full md:w-48 space-y-4 shrink-0 flex flex-col items-stretch md:items-end justify-center">
          <div className="w-full space-y-1">
            <div className="flex items-center justify-between text-[11px] font-mono text-muted-foreground/60">
              <span>RELEVANCE</span>
              <span>{progressVal}%</span>
            </div>
            <div className="h-1.5 w-full bg-border rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${getProgressColor(topic.slug)}`}
                style={{ width: `${progressVal}%` }}
              />
            </div>
          </div>

          <Link
            href={`/topics/${topic.slug}`}
            className="w-full md:w-auto inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg border border-neutral-300 dark:border-neutral-700 bg-transparent text-neutral-900 dark:text-neutral-100 hover:bg-black/5 dark:hover:bg-white/5 font-mono text-xs uppercase tracking-wider transition-colors shadow-sm focus-visible:ring-2 focus-visible:ring-neutral-950 dark:focus-visible:ring-white outline-none"
          >
            View All <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </m.div>
    );
  }

  return (
    <m.div
      whileHover={{ y: -4 }}
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
      className="rounded-xl border border-border bg-card/65 dark:bg-card/40 hover:bg-card/90 dark:hover:bg-card/75 text-card-foreground p-5 shadow-sm hover:shadow-md hover:border-black/20 dark:hover:border-white/20 hover:shadow-black/10 dark:hover:shadow-white/10 transition-all flex flex-col justify-between focus-within:ring-2 focus-within:ring-neutral-950 dark:focus-within:ring-white/50 outline-none select-none h-full min-h-[260px] relative"
    >
      <div className="space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className={`p-3 rounded-xl bg-gradient-to-br ${theme.colorClass} ${theme.textClass} shrink-0`}>
              <IconComponent className="w-5.5 h-5.5" />
            </div>
            
            <div className="space-y-0.5">
              <h3 className="text-base font-bold tracking-tight text-foreground line-clamp-1">
                {topic.name}
              </h3>
              <div className="flex items-center gap-1.5 text-[10px] font-mono text-muted-foreground/60">
                <span>{topic.totalCount} {topic.totalCount === 1 ? "Article" : "Articles"}</span>
                {topic.lastUpdated && (
                  <>
                    <span>•</span>
                    <span className="line-clamp-1">{topic.lastUpdated}</span>
                  </>
                )}
              </div>
            </div>
          </div>

          <button
            onClick={toggleFav}
            className="text-muted-foreground/40 hover:text-yellow-500 transition-colors p-1 shrink-0"
            aria-label={isFav ? `Unfavorite ${topic.name}` : `Favorite ${topic.name}`}
          >
            <Star
              className={`w-4 h-4 transition-all duration-300 ${
                mounted && isFav ? "fill-yellow-500 text-yellow-500 scale-110" : "text-muted-foreground/60 hover:scale-105"
              }`}
            />
          </button>
        </div>

        <p className="text-sm text-muted-foreground/75 leading-relaxed line-clamp-3">
          {description}
        </p>
      </div>

      <div className="space-y-4 pt-4 border-t border-border/40 mt-4">
        <div className="space-y-1">
          <div className="flex items-center justify-between text-[9px] font-mono text-muted-foreground/50 tracking-wider">
            <span>RELEVANCE COVERAGE</span>
            <span>{progressVal}%</span>
          </div>
          <div className="h-1 w-full bg-border/50 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${getProgressColor(topic.slug)}`}
              style={{ width: `${progressVal}%` }}
            />
          </div>
        </div>

        <Link
          href={`/topics/${topic.slug}`}
          className="w-full inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-700 bg-transparent text-neutral-900 dark:text-neutral-100 hover:bg-black/5 dark:hover:bg-white/5 font-mono text-[10px] uppercase tracking-wider transition-colors shadow-sm focus-visible:ring-2 focus-visible:ring-neutral-950 dark:focus-visible:ring-white outline-none"
        >
          View All <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    </m.div>
  );
}

TopicCard.displayName = "TopicCard";
