"use client";

import React, { useState, useMemo, useEffect } from "react";
import { AnimatePresence, m } from "framer-motion";
import { Search, X, Check, Building2, Newspaper, Users, Plus } from "lucide-react";
import { SourceItem } from "@/hooks/useSourceFollow";

interface SourceSelectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  sources: SourceItem[];
  onToggleFollow: (sourceId: number) => void;
  isToggling?: boolean;
}

const EASE_CUBIC = [0.16, 1, 0.3, 1] as const;

export function SourceSelectorModal({
  isOpen,
  onClose,
  sources,
  onToggleFollow,
  isToggling,
}: SourceSelectorModalProps) {
  const [searchQuery, setSearchQuery] = useState("");

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

  // Filter sources by search query
  const filteredSources = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return sources;
    return sources.filter(
      (s) =>
        s.name.toLowerCase().includes(q) ||
        (s.slug && s.slug.toLowerCase().includes(q)) ||
        (s.description && s.description.toLowerCase().includes(q))
    );
  }, [sources, searchQuery]);

  // Group by category
  const officialSources = filteredSources.filter((s) => s.category === "official");
  const editorialSources = filteredSources.filter((s) => s.category === "editorial");
  const communitySources = filteredSources.filter((s) => s.category === "community");

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
        {/* Backdrop */}
        <m.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          onClick={onClose}
          className="fixed inset-0 bg-black/75 backdrop-blur-md"
          aria-hidden="true"
        />

        {/* Modal Window */}
        <m.div
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-sources-title"
          initial={{ opacity: 0, scale: 0.96, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.96, y: 15 }}
          transition={{ duration: 0.3, ease: EASE_CUBIC }}
          className="relative w-full max-w-2xl max-h-[85vh] flex flex-col rounded-2xl bg-zinc-950 border border-white/15 shadow-2xl shadow-black/80 overflow-hidden z-10"
        >
          {/* Header */}
          <div className="flex items-start justify-between p-6 border-b border-white/10">
            <div className="space-y-1 pr-6">
              <h3 id="modal-sources-title" className="text-xl sm:text-2xl font-sans font-bold tracking-tight text-foreground">
                Follow Technology Sources
              </h3>
              <p className="text-xs text-muted-foreground font-mono">
                Choose the official newsrooms and editorial publishers to include in your feed.
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-white/10 transition-all cursor-pointer"
              aria-label="Close dialog"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Search Bar */}
          <div className="p-4 sm:px-6 border-b border-white/10 bg-white/[0.02]">
            <div className="relative flex items-center w-full">
              <Search className="absolute left-3.5 w-4 h-4 text-muted-foreground/60 pointer-events-none" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search sources (Google, OpenAI, Anthropic, NVIDIA...)"
                className="w-full pl-10 pr-10 py-2.5 rounded-xl bg-white/[0.05] border border-white/10 text-sm font-sans placeholder:text-muted-foreground/50 text-foreground focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery("")}
                  className="absolute right-3 p-1 rounded-md text-muted-foreground hover:text-foreground"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>

          {/* Sources List Content */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6 divide-y divide-white/5">
            {filteredSources.length === 0 ? (
              <div className="py-12 text-center space-y-2">
                <p className="text-sm font-medium text-foreground">No sources matched &ldquo;{searchQuery}&rdquo;</p>
                <p className="text-xs text-muted-foreground font-mono">Try searching by company or publisher name.</p>
              </div>
            ) : (
              <>
                {/* Official Newsrooms */}
                {officialSources.length > 0 && (
                  <div className="space-y-3 pt-3 first:pt-0">
                    <div className="flex items-center gap-2 text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground/80">
                      <Building2 className="w-3.5 h-3.5 text-primary/80" />
                      <span>Official Company Newsrooms</span>
                    </div>
                    <div className="grid grid-cols-1 gap-2">
                      {officialSources.map((source) => (
                        <SourceRow
                          key={source.id}
                          source={source}
                          onToggleFollow={onToggleFollow}
                          isToggling={isToggling}
                        />
                      ))}
                    </div>
                  </div>
                )}

                {/* Major Tech Publications */}
                {editorialSources.length > 0 && (
                  <div className="space-y-3 pt-5">
                    <div className="flex items-center gap-2 text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground/80">
                      <Newspaper className="w-3.5 h-3.5 text-emerald-400/80" />
                      <span>Major Tech Publications</span>
                    </div>
                    <div className="grid grid-cols-1 gap-2">
                      {editorialSources.map((source) => (
                        <SourceRow
                          key={source.id}
                          source={source}
                          onToggleFollow={onToggleFollow}
                          isToggling={isToggling}
                        />
                      ))}
                    </div>
                  </div>
                )}

                {/* Community Feeds */}
                {communitySources.length > 0 && (
                  <div className="space-y-3 pt-5">
                    <div className="flex items-center gap-2 text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground/80">
                      <Users className="w-3.5 h-3.5 text-indigo-400/80" />
                      <span>Community Discussions</span>
                    </div>
                    <div className="grid grid-cols-1 gap-2">
                      {communitySources.map((source) => (
                        <SourceRow
                          key={source.id}
                          source={source}
                          onToggleFollow={onToggleFollow}
                          isToggling={isToggling}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between px-6 py-4 border-t border-white/10 bg-white/[0.02]">
            <span className="text-xs font-mono text-muted-foreground/70">
              {sources.filter((s) => s.is_following).length} followed
            </span>
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/15 text-xs font-mono font-semibold text-foreground border border-white/10 transition-all cursor-pointer"
            >
              Done
            </button>
          </div>
        </m.div>
      </div>
    </AnimatePresence>
  );
}

function SourceRow({
  source,
  onToggleFollow,
  isToggling,
}: {
  source: SourceItem;
  onToggleFollow: (id: number) => void;
  isToggling?: boolean;
}) {
  return (
    <div className="flex items-center justify-between p-3 sm:p-3.5 rounded-xl bg-white/[0.02] hover:bg-white/[0.05] border border-white/5 hover:border-white/10 transition-all group">
      <div className="flex flex-col gap-0.5 pr-4">
        <div className="flex items-center gap-2">
          <span className="text-sm font-sans font-semibold text-foreground group-hover:text-primary transition-colors">
            {source.name}
          </span>
          {source.category === "official" && (
            <span className="text-[10px] font-mono font-medium px-1.5 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
              Official
            </span>
          )}
        </div>
        {source.description && (
          <p className="text-xs text-muted-foreground/75 font-sans line-clamp-1">
            {source.description}
          </p>
        )}
      </div>

      <button
        type="button"
        onClick={() => onToggleFollow(source.id)}
        disabled={isToggling}
        className={`shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-semibold transition-all cursor-pointer ${
          source.is_following
            ? "bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm"
            : "bg-white/5 hover:bg-white/10 text-muted-foreground hover:text-foreground border border-white/10"
        }`}
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
