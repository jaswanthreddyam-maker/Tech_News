"use client";

import React, { useState, useMemo, useEffect } from "react";
import { AnimatePresence, m } from "framer-motion";
import { Search, X, Check, Building2, Newspaper, Users, Plus } from "lucide-react";
import { SourceItem } from "@/hooks/useSourceFollow";

interface SourceSelectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  sources: SourceItem[];
  onToggleFollow: (sourceSlug: string) => void;
  isToggling?: boolean;
}

const EASE_CUBIC = [0.16, 1, 0.3, 1] as const;

export const FALLBACK_SOURCES: SourceItem[] = [
  { slug: "google", name: "Google Blog", category: "official", description: "Official news, research, and announcements from Google.", logo_url: null, url: "https://blog.google/rss/", credibility_score: 0.95, is_following: false },
  { slug: "openai", name: "OpenAI Blog", category: "official", description: "Frontier AI research, product updates, and system cards from OpenAI.", logo_url: null, url: "https://openai.com/news/rss.xml", credibility_score: 0.95, is_following: false },
  { slug: "anthropic", name: "Anthropic News", category: "official", description: "Claude model releases, safety alignment, and frontier research from Anthropic.", logo_url: null, url: "https://www.anthropic.com/news/rss", credibility_score: 0.95, is_following: false },
  { slug: "nvidia", name: "NVIDIA AI Blog", category: "official", description: "GPU architectures, CUDA, accelerated computing, and deep learning from NVIDIA.", logo_url: null, url: "https://blogs.nvidia.com/feed/", credibility_score: 0.95, is_following: false },
  { slug: "microsoft", name: "Microsoft Blog", category: "official", description: "Official news, Azure AI infrastructure, and engineering updates from Microsoft.", logo_url: null, url: "https://blogs.microsoft.com/feed/", credibility_score: 0.95, is_following: false },
  { slug: "meta", name: "Meta Newsroom", category: "official", description: "Open source AI models (Llama), PyTorch, and reality labs research from Meta.", logo_url: null, url: "https://about.fb.com/news/feed/", credibility_score: 0.95, is_following: false },
  { slug: "apple", name: "Apple Newsroom", category: "official", description: "Official hardware, software, Apple Silicon, and OS platform releases.", logo_url: null, url: "https://www.apple.com/newsroom/rss-feed.rss", credibility_score: 0.95, is_following: false },
  { slug: "techcrunch", name: "TechCrunch", category: "editorial", description: "Breaking technology journalism, startup funding, and venture capital reporting.", logo_url: null, url: "https://techcrunch.com/feed/", credibility_score: 0.9, is_following: false },
  { slug: "the-verge", name: "The Verge", category: "editorial", description: "Technology culture, reviews, gadget analysis, and tech policy reporting.", logo_url: null, url: "https://www.theverge.com/rss/index.xml", credibility_score: 0.9, is_following: false },
  { slug: "ars-technica", name: "Ars Technica", category: "editorial", description: "Deep technical analysis, cybersecurity, science, and computing architecture.", logo_url: null, url: "https://feeds.arstechnica.com/arstechnica/index", credibility_score: 0.92, is_following: false },
  { slug: "mit-technology-review", name: "MIT Technology Review", category: "editorial", description: "Authoritative reporting on commercial, political, and social impact of tech.", logo_url: null, url: "https://www.technologyreview.com/feed/", credibility_score: 0.94, is_following: false },
];

export function SourceSelectorModal({
  isOpen,
  onClose,
  sources,
  onToggleFollow,
  isToggling,
}: SourceSelectorModalProps) {
  const [searchQuery, setSearchQuery] = useState("");

  // Use provided sources if available, otherwise fallback
  const effectiveSources = useMemo(() => {
    if (sources && sources.length > 0) return sources;
    return FALLBACK_SOURCES;
  }, [sources]);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // Prevent background body scroll when modal is active
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  // Filter sources by search query
  const filteredSources = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return effectiveSources;
    return effectiveSources.filter(
      (s) =>
        s.name.toLowerCase().includes(q) ||
        (s.slug && s.slug.toLowerCase().includes(q)) ||
        (s.description && s.description.toLowerCase().includes(q))
    );
  }, [effectiveSources, searchQuery]);

  // Group by category
  const officialSources = filteredSources.filter((s) => s.category === "official");
  const editorialSources = filteredSources.filter((s) => s.category === "editorial");
  const communitySources = filteredSources.filter((s) => s.category === "community");
  const otherSources = filteredSources.filter(
    (s) => s.category !== "official" && s.category !== "editorial" && s.category !== "community"
  );

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
          {/* Backdrop */}
          <m.div
            key="modal-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm"
          />

          {/* Modal Card */}
          <m.div
            key="modal-card"
            initial={{ opacity: 0, scale: 0.96, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 10 }}
            transition={{ duration: 0.25, ease: EASE_CUBIC }}
            className="relative w-full max-w-2xl bg-neutral-900 border border-neutral-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh] z-10"
            role="dialog"
            aria-modal="true"
            aria-labelledby="source-selector-title"
          >
            {/* Header */}
            <div className="p-6 border-b border-neutral-800/80 flex items-center justify-between gap-4">
              <div>
                <h2 id="source-selector-title" className="text-xl font-bold text-neutral-100 tracking-tight">
                  Follow Authoritative Sources
                </h2>
                <p className="text-sm text-neutral-400 mt-1">
                  Select primary technology engineering blogs and editorial publishers for your feed.
                </p>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="p-2 text-neutral-400 hover:text-neutral-100 hover:bg-neutral-800 rounded-xl transition-colors focus:outline-none focus:ring-2 focus:ring-amber-500/50"
                aria-label="Close dialog"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Search Input */}
            <div className="p-4 border-b border-neutral-800/50 bg-neutral-900/50">
              <div className="relative">
                <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-500" />
                <input
                  type="text"
                  placeholder="Search sources by name or description..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 bg-neutral-800/60 border border-neutral-700/60 rounded-xl text-neutral-100 placeholder-neutral-500 text-sm focus:outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/50 transition-colors"
                />
                {searchQuery && (
                  <button
                    type="button"
                    onClick={() => setSearchQuery("")}
                    className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-neutral-400 hover:text-neutral-200"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>

            {/* Sources List by Categories */}
            <div className="p-6 overflow-y-auto flex-1 space-y-6">
              {filteredSources.length === 0 ? (
                <div className="py-12 text-center">
                  <p className="text-neutral-400 text-sm">No sources found matching &ldquo;{searchQuery}&rdquo;</p>
                </div>
              ) : (
                <>
                  {officialSources.length > 0 && (
                    <CategorySection
                      title="Official Engineering & Research"
                      icon={<Building2 className="w-4 h-4 text-amber-400" />}
                      sources={officialSources}
                      onToggleFollow={onToggleFollow}
                      isToggling={isToggling}
                    />
                  )}

                  {editorialSources.length > 0 && (
                    <CategorySection
                      title="Editorial & Journalism"
                      icon={<Newspaper className="w-4 h-4 text-sky-400" />}
                      sources={editorialSources}
                      onToggleFollow={onToggleFollow}
                      isToggling={isToggling}
                    />
                  )}

                  {communitySources.length > 0 && (
                    <CategorySection
                      title="Community & Research Hubs"
                      icon={<Users className="w-4 h-4 text-emerald-400" />}
                      sources={communitySources}
                      onToggleFollow={onToggleFollow}
                      isToggling={isToggling}
                    />
                  )}

                  {otherSources.length > 0 && (
                    <CategorySection
                      title="Other Sources"
                      icon={<Building2 className="w-4 h-4 text-purple-400" />}
                      sources={otherSources}
                      onToggleFollow={onToggleFollow}
                      isToggling={isToggling}
                    />
                  )}
                </>
              )}
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-neutral-800 bg-neutral-900/90 flex items-center justify-between">
              <span className="text-xs text-neutral-500">
                Following {effectiveSources.filter((s) => s.is_following).length} of {effectiveSources.length} sources
              </span>
              <button
                type="button"
                onClick={onClose}
                className="px-5 py-2 bg-amber-500 hover:bg-amber-400 text-neutral-950 font-semibold text-sm rounded-xl transition-colors shadow-sm"
              >
                Done
              </button>
            </div>
          </m.div>
        </div>
      )}
    </AnimatePresence>
  );
}

interface CategorySectionProps {
  title: string;
  icon: React.ReactNode;
  sources: SourceItem[];
  onToggleFollow: (sourceSlug: string) => void;
  isToggling?: boolean;
}

function CategorySection({ title, icon, sources, onToggleFollow, isToggling }: CategorySectionProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-xs font-semibold text-neutral-400 uppercase tracking-wider">
        {icon}
        <span>{title}</span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {sources.map((source) => (
          <SourceCard
            key={source.slug}
            source={source}
            onToggleFollow={onToggleFollow}
            isToggling={isToggling}
          />
        ))}
      </div>
    </div>
  );
}

interface SourceCardProps {
  source: SourceItem;
  onToggleFollow: (sourceSlug: string) => void;
  isToggling?: boolean;
}

function SourceCard({ source, onToggleFollow, isToggling }: SourceCardProps) {
  return (
    <div
      className={`p-3.5 rounded-xl border transition-all flex items-start justify-between gap-3 ${
        source.is_following
          ? "bg-amber-500/5 border-amber-500/30 text-neutral-100"
          : "bg-neutral-800/40 hover:bg-neutral-800/70 border-neutral-800/80 text-neutral-300"
      }`}
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-sm truncate text-neutral-100">{source.name}</span>
          {source.category === "official" && (
            <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20 shrink-0">
              Official
            </span>
          )}
        </div>
        {source.description && (
          <p className="text-xs text-neutral-400 mt-1 line-clamp-2 leading-relaxed">
            {source.description}
          </p>
        )}
      </div>

      <button
        type="button"
        onClick={() => onToggleFollow(source.slug)}
        disabled={isToggling}
        className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 shrink-0 transition-all focus:outline-none focus:ring-2 focus:ring-amber-500/50 ${
          source.is_following
            ? "bg-amber-500/20 text-amber-300 border border-amber-500/40 hover:bg-amber-500/30"
            : "bg-neutral-700 hover:bg-neutral-600 text-neutral-200"
        }`}
        aria-pressed={source.is_following}
      >
        {source.is_following ? (
          <>
            <Check className="w-3.5 h-3.5" />
            <span>Following</span>
          </>
        ) : (
          <>
            <Plus className="w-3.5 h-3.5" />
            <span>Follow</span>
          </>
        )}
      </button>
    </div>
  );
}
