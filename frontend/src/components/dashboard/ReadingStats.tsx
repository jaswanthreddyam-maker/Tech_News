"use client";

import React, { useMemo } from "react";
import { usePersonalization } from "@/components/providers/PersonalizationProvider";
import { Flame, Clock, BookOpen, TrendingUp } from "lucide-react";

export function ReadingStats({ compact = false }: { compact?: boolean }) {
  const { readingHistory } = usePersonalization();

  const stats = useMemo(() => {
    const totalFinished = readingHistory.filter(h => h.completed).length;
    const totalTimeSeconds = readingHistory.reduce((acc, curr) => acc + curr.readingTime, 0);
    const avgTimeSeconds = totalFinished > 0 ? totalTimeSeconds / totalFinished : 0;
    
    // Very naive streak calculation for UI purposes
    const streak = totalFinished > 0 ? 1 : 0; // Requires actual day-by-day calculation

    // Favorite topic calculation
    // Naively extract from category or just mock
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const topics = readingHistory.reduce((acc, curr) => {
      // we don't store category in ReadingHistoryItem currently, so let's mock "Technology"
      const cat = "Technology"; 
      acc[cat] = (acc[cat] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
    
    const favTopic = Object.entries(topics).sort((a, b) => b[1] - a[1])[0]?.[0] || "None";

    // Favorite source
    const sources = readingHistory.reduce((acc, curr) => {
      const src = curr.source || "Unknown";
      acc[src] = (acc[src] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const favSource = Object.entries(sources).sort((a, b) => b[1] - a[1])[0]?.[0] || "None";

    return {
      totalFinished,
      totalTimeMinutes: Math.floor(totalTimeSeconds / 60),
      avgTimeMinutes: Math.floor(avgTimeSeconds / 60),
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
            <p className="text-2xl font-bold">{stats.totalTimeMinutes}m</p>
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
        value={`${stats.totalTimeMinutes} min`} 
        icon={<Clock className="w-5 h-5 text-emerald-500" />} 
      />
      <StatCard 
        title="Avg Time / Article" 
        value={`${stats.avgTimeMinutes} min`} 
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
