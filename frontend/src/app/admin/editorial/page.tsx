"use client";

import React, { useState, useEffect } from "react";
import { apiFetch } from "@/services/api";
import { 
  TrendingUp, 
  AlertCircle, 
  Clock, 
  Archive, 
  BarChart2, 
  Search, 
  ChevronRight,
  Zap
} from "lucide-react";

// Types matching the new backend
interface OverviewPayload {
  active_stories: number;
  needs_review: number;
}

interface TopStory {
  story_id: string;
  title: string;
  status: string;
  editorial_status: string;
  unique_readers: number;
  avg_completion_rate?: number;
  views: number;
  bookmarks: number;
}

interface CoverageGap {
  topic: string;
  coverage: string;
  search_volume: string;
}

function SectionHeading({ title, icon: Icon, badge }: { title: string, icon: any, badge?: number }) {
  return (
    <div className="flex items-center gap-3 mb-6 border-b border-[#222] pb-3">
      <div className="p-1.5 bg-[#111] rounded-md text-[#888]">
        <Icon size={18} />
      </div>
      <h2 className="text-sm font-mono tracking-widest uppercase text-[#ccc] font-bold">
        {title}
      </h2>
      {badge !== undefined && (
        <span className="ml-auto bg-emerald-500/10 text-emerald-400 font-mono text-[10px] px-2 py-0.5 rounded-full border border-emerald-500/20">
          {badge}
        </span>
      )}
    </div>
  );
}

interface CalibrationStatus {
  status: string;
  observation_window_days_completed: number;
  observation_window_days_total: number;
  tracked_stories: number;
  total_snapshots: number;
  expected_activation_date: string;
}

export default function NewsroomDashboard() {
  const [overview, setOverview] = useState<OverviewPayload | null>(null);
  const [topStories, setTopStories] = useState<TopStory[]>([]);
  const [reviewQueue, setReviewQueue] = useState<any>({ article_drafts: [], assignment_reviews: [] });
  const [dormantData, setDormantData] = useState<any>({ dormant_stories: [], reawakening_candidates: [] });
  const [gaps, setGaps] = useState<CoverageGap[]>([]);
  const [calibration, setCalibration] = useState<CalibrationStatus | null>(null);
  const [activeStoryId, setActiveStoryId] = useState<string | null>(null);

  // Independent fetchers
  useEffect(() => {
    apiFetch<OverviewPayload>("/admin/editorial/overview").then(res => setOverview(res)).catch(() => {});
    apiFetch<TopStory[]>("/admin/editorial/top-stories?limit=5").then(res => setTopStories(res)).catch(() => {});
    apiFetch<any>("/admin/editorial/review-queue").then(res => setReviewQueue(res)).catch(() => {});
    apiFetch<any>("/admin/editorial/dormant").then(res => setDormantData(res)).catch(() => {});
    apiFetch<any>("/admin/editorial/coverage-gaps").then(res => setGaps(res?.gaps || [])).catch(() => {});
    apiFetch<CalibrationStatus>("/admin/editorial/calibration-status").then(res => setCalibration(res)).catch(() => {});
    
    // SSE Stream
    const eventSource = new EventSource("/api/v1/admin/editorial/events");
    eventSource.onmessage = (event) => {
      console.log("Real-time Editorial Event:", event.data);
      // In a full implementation, we'd dispatch this to Redux or trigger a localized re-fetch
      // e.g. if event.type === 'AssignmentReviewCreated', fetch review-queue again
    };
    return () => eventSource.close();
  }, []);

  return (
    <div className="p-6 md:p-8 space-y-8 bg-black min-h-screen text-white selection:bg-emerald-500/30">
      
      {/* Header */}
      <header className="flex items-end justify-between mb-10">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            <span className="h-4 w-4 bg-emerald-500 rounded-sm animate-pulse shadow-[0_0_15px_rgba(16,185,129,0.5)]"></span>
            Newsroom Command
          </h1>
          <p className="text-[#666] font-mono text-xs mt-2 uppercase tracking-widest">
            Editorial Intelligence & Narrative Tracking
          </p>
        </div>
      </header>

      {/* Calibration Widget */}
      {calibration && (
        <div className="bg-[#0a0a0a] border border-blue-500/30 rounded-xl p-6 shadow-[0_0_20px_rgba(59,130,246,0.05)] relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/10 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/3"></div>
          <div className="flex items-center gap-4 mb-4">
            <div className="p-2 bg-blue-500/10 rounded-lg"><BarChart2 className="text-blue-400" size={24} /></div>
            <div>
              <h2 className="text-lg font-semibold text-blue-100 tracking-tight">Impact Engine Calibration</h2>
              <p className="text-xs font-mono text-blue-400/80 uppercase">Phase: Collecting Data</p>
            </div>
            <div className="ml-auto text-right font-mono">
              <p className="text-[10px] text-blue-300/50 uppercase tracking-widest">Next Milestone</p>
              <p className="text-blue-200 font-bold">Calibration Report Generation</p>
            </div>
          </div>
          <div className="grid grid-cols-4 gap-4 mt-6">
            <div className="border border-[#222] bg-black/40 rounded px-4 py-3">
              <p className="text-[10px] font-mono text-[#666] mb-1">OBSERVATION WINDOW</p>
              <p className="text-xl font-bold text-white/90">{calibration.observation_window_days_completed} <span className="text-sm text-[#555]">/ {calibration.observation_window_days_total} Days</span></p>
            </div>
            <div className="border border-[#222] bg-black/40 rounded px-4 py-3">
              <p className="text-[10px] font-mono text-[#666] mb-1">TRACKED STORIES</p>
              <p className="text-xl font-bold text-white/90">{calibration.tracked_stories.toLocaleString()}</p>
            </div>
            <div className="border border-[#222] bg-black/40 rounded px-4 py-3">
              <p className="text-[10px] font-mono text-[#666] mb-1">SNAPSHOTS GATHERED</p>
              <p className="text-xl font-bold text-white/90">{calibration.total_snapshots.toLocaleString()}</p>
            </div>
            <div className="border border-[#222] bg-black/40 rounded px-4 py-3 flex items-center justify-center">
              <div className="w-full h-1.5 bg-[#111] rounded-full overflow-hidden">
                <div 
                  className="h-full bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.8)] rounded-full transition-all duration-1000" 
                  style={{ width: `${(calibration.observation_window_days_completed / calibration.observation_window_days_total) * 100}%` }}
                ></div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">
        
        {/* Left Column: Top Stories & Dormant */}
        <div className="xl:col-span-8 space-y-8">
          
          {/* Top Stories */}
          <section className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-xl p-6 shadow-2xl relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/5 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/3 group-hover:bg-emerald-500/10 transition-colors duration-1000"></div>
            
            <SectionHeading title="Top Performing Stories" icon={TrendingUp} />
            
            <div className="space-y-3">
              {topStories.map((story, idx) => (
                <button
                  type="button"
                  key={story.story_id} 
                  onClick={() => setActiveStoryId(story.story_id)}
                  className="group/item w-full text-left flex items-center gap-4 p-4 rounded-lg bg-black/50 border border-[#1a1a1a] hover:border-emerald-500/30 cursor-pointer transition-all duration-300"
                >
                  <div className="font-mono text-2xl text-[#333] font-bold w-8 text-right group-hover/item:text-emerald-500/50 transition-colors">
                    {idx + 1}
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-white/90 group-hover/item:text-emerald-400 transition-colors">{story.title}</h3>
                    <div className="flex items-center gap-4 mt-2">
                      <span className="text-xs font-mono text-[#666]">VIEWS: <span className="text-white/70">{story.views.toLocaleString()}</span></span>
                      <span className="text-xs font-mono text-[#666]">READERS: <span className="text-white/70">{story.unique_readers.toLocaleString()}</span></span>
                      <span className="text-xs font-mono text-[#666]">BKMK: <span className="text-white/70">{story.bookmarks.toLocaleString()}</span></span>
                    </div>
                  </div>
                  <button className="h-8 w-8 rounded bg-[#111] flex items-center justify-center text-[#555] group-hover/item:bg-emerald-500/10 group-hover/item:text-emerald-400 transition-all">
                    <ChevronRight size={16} />
                  </button>
                </button>
              ))}
              {topStories.length === 0 && <div className="text-center p-8 font-mono text-sm text-[#444]">Loading telemetry projection...</div>}
            </div>
          </section>

          {/* Dormant & Reawakening */}
          <section className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-xl p-6 shadow-2xl">
            <SectionHeading title="Dormant Narratives & Reawakenings" icon={Archive} />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              
              {/* Reawakening Candidates */}
              <div className="border border-blue-500/20 bg-blue-500/5 rounded-lg p-4 relative overflow-hidden">
                <div className="absolute top-0 right-0 p-2 opacity-10"><Zap size={48} /></div>
                <h4 className="font-mono text-xs text-blue-400 tracking-wider mb-4 font-bold flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-ping"></span>
                  REAWAKENING CANDIDATES
                </h4>
                {dormantData.reawakening_candidates.length > 0 ? (
                  <ul className="space-y-2">
                    {dormantData.reawakening_candidates.map((c: any, i: number) => (
                      <li key={i} className="text-sm text-white/80 p-2 bg-black/40 rounded border border-blue-500/10">
                        {c.title}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-[#555] font-mono italic">No strong signals detected.</p>
                )}
              </div>

              {/* Standard Dormant */}
              <div className="border border-[#222] bg-black/40 rounded-lg p-4">
                <h4 className="font-mono text-xs text-[#666] tracking-wider mb-4 font-bold">RECENTLY DORMANT</h4>
                <ul className="space-y-2">
                  {dormantData.dormant_stories.slice(0, 3).map((story: any) => (
                    <li key={story.story_id} className="text-sm text-[#888] truncate hover:text-[#bbb] cursor-pointer transition-colors">
                      {story.title}
                    </li>
                  ))}
                </ul>
              </div>

            </div>
          </section>
        </div>

        {/* Right Column: Review Queue & Gaps */}
        <div className="xl:col-span-4 space-y-8">
          
          {/* Action Queue */}
          <section className="bg-[#0a0a0a] border border-amber-500/20 rounded-xl p-6 shadow-[0_0_30px_rgba(245,158,11,0.03)] relative">
            <div className="absolute top-0 right-0 w-full h-1 bg-gradient-to-r from-amber-500/0 via-amber-500/50 to-amber-500/0 opacity-50"></div>
            <SectionHeading 
              title="Action Queue" 
              icon={AlertCircle} 
              badge={(reviewQueue.article_drafts.length + reviewQueue.assignment_reviews.length) || 0} 
            />
            
            <div className="space-y-6">
              <div>
                <h4 className="font-mono text-[10px] text-[#555] mb-3 tracking-widest">ASSIGNMENT REVIEWS</h4>
                <div className="space-y-2">
                  {reviewQueue.assignment_reviews.length === 0 ? (
                    <div className="text-xs text-[#444] font-mono">Clear.</div>
                  ) : (
                    reviewQueue.assignment_reviews.map((rev: any, i: number) => (
                      <div key={i} className="p-3 bg-amber-500/5 border border-amber-500/20 rounded-lg">
                        <p className="text-sm text-amber-100/90 mb-2 truncate">Match Confidence: <span className="text-amber-400 font-mono">{rev.similarity_score}</span></p>
                        <div className="flex gap-2">
                          <button className="flex-1 bg-amber-500/20 hover:bg-amber-500/30 text-amber-500 text-xs py-1.5 rounded transition-colors">Approve</button>
                          <button className="flex-1 bg-black hover:bg-[#111] text-[#888] border border-[#333] text-xs py-1.5 rounded transition-colors">Reject</button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <div>
                <h4 className="font-mono text-[10px] text-[#555] mb-3 tracking-widest">DRAFTS</h4>
                <div className="space-y-2">
                  {reviewQueue.article_drafts.length === 0 ? (
                    <div className="text-xs text-[#444] font-mono">Clear.</div>
                  ) : (
                    reviewQueue.article_drafts.map((draft: any) => (
                      <div key={draft.id} className="p-3 bg-[#111] border border-[#222] rounded-lg cursor-pointer hover:border-[#444] transition-colors">
                        <p className="text-sm text-[#ddd] truncate">{draft.title}</p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </section>

              {/* Coverage Gaps */}
          <section className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-xl p-6">
            <SectionHeading title="Coverage Gaps" icon={Search} />
            <div className="space-y-3">
              {gaps.map((gap, i) => {
                const isCritical = gap.search_volume === 'HIGH' && gap.coverage === 'LOW';
                return (
                  <div key={i} className={`flex items-center justify-between p-3 rounded-lg border ${isCritical ? 'bg-red-500/5 border-red-500/20' : 'bg-[#111] border-[#222]'}`}>
                    <span className={`font-semibold text-sm ${isCritical ? 'text-red-200' : 'text-[#aaa]'}`}>{gap.topic}</span>
                    <div className="flex gap-2">
                      <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded ${gap.search_volume === 'HIGH' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-[#222] text-[#666]'}`}>
                        SRCH: {gap.search_volume}
                      </span>
                      <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded ${gap.coverage === 'LOW' ? 'bg-red-500/20 text-red-400' : 'bg-[#222] text-[#666]'}`}>
                        COV: {gap.coverage}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

        </div>
      </div>
      
      {/* Story Graph Modal Placeholder */}
      {activeStoryId && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 md:p-12">
          <div className="bg-[#0a0a0a] border border-[#222] rounded-xl w-full max-w-5xl h-[80vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="p-4 border-b border-[#222] flex justify-between items-center bg-[#111]">
              <h2 className="font-mono text-emerald-400 text-sm tracking-widest font-bold flex items-center gap-2">
                <Search size={16} />
                STORY GRAPH VISUALIZATION
              </h2>
              <button 
                onClick={() => setActiveStoryId(null)}
                className="text-[#666] hover:text-white transition-colors"
              >
                Close
              </button>
            </div>
            <div className="flex-1 p-8 flex items-center justify-center relative bg-[url('/grid.svg')] bg-center">
              {/* Minimal placeholder for the graph */}
              <div className="text-center space-y-4 relative z-10">
                <div className="w-24 h-24 border-2 border-emerald-500/30 rounded-full mx-auto flex items-center justify-center bg-emerald-500/10 shadow-[0_0_30px_rgba(16,185,129,0.2)]">
                  <span className="text-emerald-400 font-mono text-xs">CORE</span>
                </div>
                <div className="flex gap-16 justify-center mt-12">
                  <div className="w-16 h-16 border border-[#333] rounded flex items-center justify-center bg-[#111]">
                    <span className="text-[#888] font-mono text-[10px]">STORY</span>
                  </div>
                  <div className="w-16 h-16 border border-[#333] rounded-full flex items-center justify-center bg-[#111]">
                    <span className="text-[#888] font-mono text-[10px]">ENTITY</span>
                  </div>
                </div>
                {/* Lines (css approximations) */}
                <div className="absolute top-[40%] left-1/2 w-0.5 h-12 bg-emerald-500/20 -translate-x-12 rotate-45"></div>
                <div className="absolute top-[40%] right-1/2 w-0.5 h-12 bg-emerald-500/20 translate-x-12 -rotate-45"></div>
                
                <p className="text-xs text-[#555] font-mono italic mt-12">
                  GraphPayload loaded for {activeStoryId}. <br/>
                  Client-side force-graph rendering will be integrated here.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
