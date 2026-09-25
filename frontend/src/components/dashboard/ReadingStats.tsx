"use client";

import React, { useMemo } from "react";
import { usePersonalization } from "@/components/providers/PersonalizationProvider";
import { Flame, Clock, BookOpen, TrendingUp } from "lucide-react";

export function ReadingStats({ compact = false }: { compact?: boolean }) {
  const { readingHistory } = usePersonalization();

  const stats = useMemo(() => {
    const totalFinished = readingHistory.filter(h => h.completed).length;
    const totalTimeSeconds = readingHistory.reduce((acc, curr) => acc + (curr.readingTime || 0), 0);
    const avgTimeSeconds = readingHistory.length > 0 ? totalTimeSeconds / readingHistory.length : 0;
    
    // Accurate day-by-day streak calculation
    let streak = 0;
    if (readingHistory.length > 0) {
      const readDates = new Set(
        readingHistory.map(h => {
          const d = new Date(h.lastReadAt || h.openedAt);
          return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
        })
      );

      const today = new Date();
      const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
      const yesterday = new Date(today);
      yesterday.setDate(yesterday.getDate() - 1);
      const yesterdayStr = `${yesterday.getFullYear()}-${String(yesterday.getMonth() + 1).padStart(2, '0')}-${String(yesterday.getDate()).padStart(2, '0')}`;

      const checkDate = readDates.has(todayStr) ? today : (readDates.has(yesterdayStr) ? yesterday : null);
      if (checkDate) {
        const cur = new Date(checkDate);
        while (true) {
          const curStr = `${cur.getFullYear()}-${String(cur.getMonth() + 1).padStart(2, '0')}-${String(cur.getDate()).padStart(2, '0')}`;
          if (readDates.has(curStr)) {
            streak++;
            cur.setDate(cur.getDate() - 1);
          } else {
            break;
          }
        }
      }
    }

    // Favorite topic calculation
    const topics = readingHistory.reduce((acc, curr) => {
      const cat = curr.topic || curr.category;
      if (cat) {
        acc[cat] = (acc[cat] || 0) + 1;
      }
      return acc;
    }, {} as Record<string, number>);
    const favTopic = Object.entries(topics).sort((a, b) => b[1] - a[1])[0]?.[0] || "None";

    // Favorite source
    const sources = readingHistory.reduce((acc, curr) => {
      const src = curr.source;
      if (src && src !== "Unknown") {
        acc[src] = (acc[src] || 0) + 1;
      }
      return acc;
    }, {} as Record<string, number>);
    const favSource = Object.entries(sources).sort((a, b) => b[1] - a[1])[0]?.[0] || "None";

    const formatTimeDisplay = (secs: number) => {
      if (!secs || secs === 0) return "0 min";
      if (secs < 60) return "< 1 min";
      return `${Math.round(secs / 60)} min`;
    };

    return {
      totalFinished,
      totalTimeDisplay: formatTimeDisplay(totalTimeSeconds),
      avgTimeDisplay: formatTimeDisplay(avgTimeSeconds),
      streak,
      favTopic,
      favSource
    };
  }, [readingHistory]);

  if (compact) {
    return (
      <div className="bg-card/50 border border-border/50 p-6 rounded-2xl">
        <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-primary" />
          Reading Overview
        </h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 bg-background/50 rounded-lg">
            <p className="text-sm text-muted-foreground font-mono uppercase tracking-wider mb-1">Finished</p>
            <p className="text-2xl font-bold">{stats.totalFinished}</p>
          </div>
          <div className="p-4 bg-background/50 rounded-lg">
            <p className="text-sm text-muted-foreground font-mono uppercase tracking-wider mb-1">Time</p>
            <p className="text-2xl font-bold">{stats.totalTimeDisplay}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
      <StatCard 
        title="Current Streak" 
        value={`${stats.streak} Days`} 
        icon={<Flame className="w-5 h-5 text-orange-500" />} 
      />
      <StatCard 
        title="Articles Finished" 
        value={stats.totalFinished.toString()} 
        icon={<BookOpen className="w-5 h-5 text-blue-500" />} 
      />
      <StatCard 
        title="Total Time" 
        value={stats.totalTimeDisplay} 
        icon={<Clock className="w-5 h-5 text-emerald-500" />} 
      />
      <StatCard 
        title="Avg Time / Article" 
        value={stats.avgTimeDisplay} 
        icon={<Clock className="w-5 h-5 text-purple-500" />} 
      />
      
      <div className="xl:col-span-2 p-6 bg-card rounded-2xl border border-border/50">
        <h4 className="text-sm font-mono uppercase tracking-widest text-muted-foreground mb-2">Favorite Topic</h4>
        <p className="text-2xl font-bold text-foreground">{stats.favTopic}</p>
      </div>
      <div className="xl:col-span-2 p-6 bg-card rounded-2xl border border-border/50">
        <h4 className="text-sm font-mono uppercase tracking-widest text-muted-foreground mb-2">Favorite Source</h4>
        <p className="text-2xl font-bold text-foreground">{stats.favSource}</p>
      </div>
    </div>
  );
}

function StatCard({ title, value, icon }: { title: string, value: string, icon: React.ReactNode }) {
  return (
    <div className="bg-card border border-border/50 p-6 rounded-2xl flex flex-col items-start justify-between min-h-[140px]">
      <div className="p-2 bg-primary/10 rounded-lg mb-4">
        {icon}
      </div>
      <div>
        <p className="text-2xl font-bold mb-1">{value}</p>
        <p className="text-sm text-muted-foreground font-mono uppercase tracking-wider">{title}</p>
      </div>
    </div>
  );
}
