"use client";

import React, { useEffect, useState, useRef } from 'react';
import Link from 'next/link';
import { ArticleLink } from "@/domains/article/ArticleLink";
import { m, useInView, useScroll, useTransform } from 'framer-motion';
import { ArrowRight, Compass } from 'lucide-react';
import { getApiBaseUrl } from "@/lib/api/getApiBaseUrl";

interface Session {
  session_id: string;
  article_id: number;
  article_title: string;
  article_slug: string;
  started_at: string;
  last_activity_at: string;
  total_reading_seconds: number;
  completion_percentage: number;
  is_completed: boolean;
}

function ReadingDeskSkeleton() {
  return (
    <div className="w-full flex flex-col items-center justify-center relative py-16 xl:py-24 min-h-[50vh]">
      <div className="flex flex-col items-center text-center mb-8 space-y-2">
        <div className="w-24 h-3 bg-white/10 rounded animate-pulse" />
        <div className="w-32 h-2.5 bg-white/5 rounded animate-pulse" />
      </div>
      <div className="relative w-full max-w-2xl px-4 flex flex-col items-center">
        <div className="w-full bg-[#0D0D0D] border border-white/[0.08] rounded-2xl p-8 sm:p-10 lg:p-12 space-y-6">
          <div className="flex justify-between border-b border-white/[0.06] pb-4">
            <div className="w-28 h-3 bg-white/10 rounded animate-pulse" />
            <div className="w-16 h-3 bg-white/5 rounded animate-pulse" />
          </div>
          <div className="space-y-3">
            <div className="w-full h-6 bg-white/10 rounded animate-pulse" />
            <div className="w-3/4 h-6 bg-white/10 rounded animate-pulse" />
          </div>
          <div className="w-full h-1.5 bg-white/10 rounded-full animate-pulse" />
          <div className="w-full h-11 bg-white/[0.05] rounded-xl animate-pulse" />
        </div>
      </div>
    </div>
  );
}

function EmptyReadingDesk() {
  const containerRef = useRef<HTMLDivElement>(null);
  const isInView = useInView(containerRef, { once: true, margin: "-20% 0px" });

  const scrollToLatestStories = () => {
    const latestStoriesEl = document.getElementById("latest-stories") || document.querySelector(".LatestStoriesSection");
    if (latestStoriesEl) {
      latestStoriesEl.scrollIntoView({ behavior: "smooth" });
    } else {
      const trendingEl = document.querySelector(".TrendingWall");
      if (trendingEl) {
        trendingEl.scrollIntoView({ behavior: "smooth" });
      } else {
        window.scrollTo({ top: window.innerHeight * 0.8, behavior: "smooth" });
      }
    }
  };

  return (
    <m.div
      ref={containerRef}
      className="w-full flex flex-col items-center justify-center relative py-16 xl:py-24 min-h-[50vh] group/desk"
    >
      {/* Environmental Ambient Vignette */}
      <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden rounded-[40px]">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_20%,rgba(0,0,0,0.7)_100%)] opacity-60" />
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[500px] h-[300px] bg-primary/5 rounded-full blur-[120px]" />
      </div>

      {/* Section Header: Your Library */}
      <m.div
        className="flex flex-col items-center text-center mb-8 z-10 space-y-1"
        initial={{ opacity: 0, y: 10 }}
        animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 10 }}
        transition={{ duration: 0.7, delay: 0.1 }}
      >
        <h2 className="text-[11px] font-mono tracking-[0.25em] text-muted-foreground/80 uppercase">
          YOUR LIBRARY
        </h2>
        <span className="text-[10px] font-mono text-muted-foreground/50">
          Personal Reading Desk
        </span>
      </m.div>

      {/* Document Workspace Container (Balanced 680px width, 2deg perspective tilt) */}
      <div className="relative w-full max-w-2xl px-4 flex flex-col items-center z-10 [perspective:1000px]">
        {/* Physical Paper Document Card (#0D0D0D matte paper finish) */}
        <m.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
          transition={{ duration: 0.7, delay: 0.3 }}
          className="relative w-full bg-[#0D0D0D] border border-white/[0.08] shadow-[inset_0_1px_1px_rgba(255,255,255,0.06),0_20px_50px_rgba(0,0,0,0.85)] rounded-2xl p-8 sm:p-10 lg:p-12 transition-all duration-500 hover:-translate-y-1.5 hover:shadow-[0_30px_70px_rgba(0,0,0,0.95)] hover:border-white/15 [transform-style:preserve-3d] [transform:rotateX(2deg)] hover:[transform:rotateX(0deg)] group/card"
        >
          {/* Subtle Paper Grain Specular Highlight */}
          <div className="absolute inset-0 bg-gradient-to-b from-white/[0.03] to-transparent pointer-events-none rounded-2xl" />

          <div className="block w-full relative z-10 text-center">
            {/* Document Metadata Header */}
            <div className="flex items-center justify-between mb-6 border-b border-white/[0.06] pb-4">
              <span className="text-[10px] font-mono tracking-[0.2em] text-primary/80 uppercase">
                DESK READY
              </span>
              <span className="text-[10px] font-mono text-muted-foreground/50 uppercase">
                NEW SESSION
              </span>
            </div>

            {/* Editorial Headline */}
            <h3 className="text-2xl sm:text-3xl font-sans font-medium leading-[1.3] tracking-tight mb-4 text-foreground/95">
              Start Your Reading Journey
            </h3>

            {/* Supporting Copy */}
            <p className="text-sm font-sans text-muted-foreground/80 leading-relaxed mb-8 max-w-lg mx-auto">
              Discover today&apos;s biggest technology stories, expert analysis, and in-depth reporting. Articles you begin reading will automatically sync here so you can continue anytime.
            </p>

            {/* Primary Action Button */}
            <button
              onClick={scrollToLatestStories}
              className="group/cta inline-flex items-center justify-center gap-2.5 w-full py-3.5 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/10 text-xs font-mono font-semibold text-foreground uppercase tracking-widest transition-all duration-300 shadow-sm cursor-pointer"
            >
              <Compass className="w-3.5 h-3.5 text-primary transition-transform duration-300 group-hover/cta:rotate-45" />
              <span>Explore Today&apos;s Latest Stories</span>
              <ArrowRight className="w-3.5 h-3.5 text-primary transition-transform duration-300 group-hover/cta:translate-x-1.5" />
            </button>
          </div>
        </m.div>
      </div>
    </m.div>
  );
}

function ReadingDeskContent({ sessions }: { sessions: Session[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const isInView = useInView(containerRef, { once: true, margin: "-20% 0px" });
  
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start end", "end start"]
  });

  // Graceful scroll exit: slide down 30px, opacity 0 when scrolling past
  const exitOpacity = useTransform(scrollYProgress, [0.75, 1], [1, 0]);
  const exitY = useTransform(scrollYProgress, [0.75, 1], [0, 30]);

  const activeSession = sessions[0];
  const estMinutesLeft = Math.max(1, Math.round((100 - (activeSession.completion_percentage || 0)) * 0.08));

  return (
    <m.div 
      ref={containerRef}
      style={{ opacity: exitOpacity, y: exitY }}
      className="w-full flex flex-col items-center justify-center relative py-16 xl:py-24 min-h-[60vh] group/desk"
    >
      {/* Environmental Ambient Vignette */}
      <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden rounded-[40px]">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_20%,rgba(0,0,0,0.7)_100%)] opacity-60" />
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[500px] h-[300px] bg-primary/5 rounded-full blur-[120px]" />
      </div>

      {/* Section Header: Your Library */}
      <m.div 
        className="flex flex-col items-center text-center mb-8 z-10 space-y-1"
        initial={{ opacity: 0, y: 10 }}
        animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 10 }}
        transition={{ duration: 0.7, delay: 0.1 }}
      >
        <h2 className="text-[11px] font-mono tracking-[0.25em] text-muted-foreground/80 uppercase">
          YOUR LIBRARY
        </h2>
        <span className="text-[10px] font-mono text-muted-foreground/50">
          Last opened • Today
        </span>
      </m.div>

      {/* Document Workspace Container (Balanced 680px width, 2deg perspective tilt) */}
      <div className="relative w-full max-w-2xl px-4 flex flex-col items-center z-10 [perspective:1000px]">
        
        {/* Physical Paper Document Card (#0D0D0D matte paper finish) */}
        <m.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
          transition={{ duration: 0.7, delay: 0.3 }}
          className="relative w-full bg-[#0D0D0D] border border-white/[0.08] shadow-[inset_0_1px_1px_rgba(255,255,255,0.06),0_20px_50px_rgba(0,0,0,0.85)] rounded-2xl p-8 sm:p-10 lg:p-12 transition-all duration-500 hover:-translate-y-1.5 hover:shadow-[0_30px_70px_rgba(0,0,0,0.95)] hover:border-white/15 [transform-style:preserve-3d] [transform:rotateX(2deg)] hover:[transform:rotateX(0deg)] group/card"
        >
          {/* Subtle Paper Grain Specular Highlight */}
          <div className="absolute inset-0 bg-gradient-to-b from-white/[0.03] to-transparent pointer-events-none rounded-2xl" />

          <ArticleLink article={{ id: activeSession.article_id, slug: activeSession.article_slug, title: activeSession.article_title } as any} section="YourLibrary" className="block w-full relative z-10">
            
            {/* Document Metadata Header */}
            <div className="flex items-center justify-between mb-6 border-b border-white/[0.06] pb-4">
              <span className="text-[10px] font-mono tracking-[0.2em] text-primary/80 uppercase">
                READING SESSION
              </span>
              <span className="text-[10px] font-mono text-muted-foreground/50 uppercase">
                {Math.max(1, Math.round(activeSession.total_reading_seconds / 60))}m read
              </span>
            </div>
            
            {/* Balanced 3-4 Line Editorial Headline */}
            <h3 className="text-2xl sm:text-3xl font-sans font-medium leading-[1.3] tracking-tight mb-8 text-foreground/95 line-clamp-3">
              {activeSession.article_title}
            </h3>
            
            {/* Progress Track */}
            <div className="space-y-2 mb-8">
              <div className="flex justify-between items-center text-[10px] font-mono text-muted-foreground/70 uppercase tracking-wider">
                <span>Reading Progress</span>
                <span>{activeSession.completion_percentage}% • {estMinutesLeft} min left</span>
              </div>

              <div className="w-full h-1.5 bg-white/10 rounded-full overflow-hidden relative">
                <m.div 
                  className="absolute top-0 left-0 h-full bg-primary/90 shadow-[0_0_12px_var(--primary)]"
                  initial={{ width: 0 }}
                  animate={isInView ? { width: `${activeSession.completion_percentage}%` } : { width: 0 }}
                  transition={{ duration: 1.2, delay: 0.6, ease: "easeOut" }}
                />
              </div>
            </div>

            {/* Primary Action Button */}
            <div className="group/cta inline-flex items-center justify-center gap-2 w-full py-3.5 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/10 text-xs font-mono font-semibold text-foreground uppercase tracking-widest transition-all duration-300 shadow-sm">
              <span>Resume Reading</span>
              <ArrowRight className="w-3.5 h-3.5 text-primary transition-transform duration-300 group-hover/cta:translate-x-1.5" />
            </div>

          </ArticleLink>
        </m.div>

      </div>
    </m.div>
  );
}

export function ResumeReading() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSessions = async () => {
      try {
        let anonId = null;
        if (typeof window !== 'undefined') {
          anonId = localStorage.getItem('tnt_anon_id');
        }
        const url = new URL(`${getApiBaseUrl()}/behavioral/sessions`);
        url.searchParams.append('status', 'in_progress');
        url.searchParams.append('limit', '3');
        if (anonId) {
          url.searchParams.append('anonymous_id', anonId);
        }
        
        const res = await fetch(url.toString());
        if (res.ok) {
          const data = await res.json();
          setSessions(data || []);
        }
      } catch (err) {
        console.error('Failed to fetch resume reading sessions:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchSessions();
  }, []);

  if (loading) {
    return <ReadingDeskSkeleton />;
  }

  if (sessions.length === 0) {
    return <EmptyReadingDesk />;
  }

  return <ReadingDeskContent sessions={sessions} />;
}
