"use client";

import React from "react";
import { usePersonalization, RecommendationSettings } from "@/components/providers/PersonalizationProvider";
import { Settings2 } from "lucide-react";

export function RecommendationSettingsForm({ compact = false }: { compact?: boolean }) {
  const { recommendationSettings, updateSettings } = usePersonalization();

  const handleToggle = (key: keyof RecommendationSettings) => {
    updateSettings({ [key]: !recommendationSettings[key] });
  };

  const handleRadio = (value: "relevance" | "freshness" | "balanced") => {
    updateSettings({ prioritize: value });
  };

  if (compact) {
    return (
      <div className="bg-card/50 border border-border/50 p-6 rounded-2xl">
        <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
          <Settings2 className="w-5 h-5 text-primary" />
          Quick Settings
        </h3>
        <div className="space-y-4">
          <label htmlFor="hideReadArticles-compact" className="flex items-center justify-between cursor-pointer group">
            <span className="text-sm font-medium group-hover:text-primary transition-colors">Hide Read Articles</span>
            <input 
              id="hideReadArticles-compact"
              type="checkbox" 
              checked={recommendationSettings.hideReadArticles}
              onChange={() => handleToggle("hideReadArticles")}
              className="w-4 h-4 accent-primary"
            />
          </label>
          <label htmlFor="preferTrustedSources-compact" className="flex items-center justify-between cursor-pointer group">
            <span className="text-sm font-medium group-hover:text-primary transition-colors">Prefer Trusted Sources</span>
            <input 
              id="preferTrustedSources-compact"
              type="checkbox" 
              checked={recommendationSettings.preferTrustedSources}
              onChange={() => handleToggle("preferTrustedSources")}
              className="w-4 h-4 accent-primary"
            />
          </label>
          <label htmlFor="showBreakingNews-compact" className="flex items-center justify-between cursor-pointer group">
            <span className="text-sm font-medium group-hover:text-primary transition-colors">Show Breaking News</span>
            <input 
              id="showBreakingNews-compact"
              type="checkbox" 
              checked={recommendationSettings.showBreakingNews}
              onChange={() => handleToggle("showBreakingNews")}
              className="w-4 h-4 accent-primary"
            />
          </label>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-2xl">
      <section className="bg-card border border-border/50 p-6 rounded-2xl">
        <h3 className="text-lg font-bold mb-6">Algorithm Priority</h3>
        <div className="space-y-4">
          {/* eslint-disable-next-line jsx-a11y/label-has-associated-control */}
          <label htmlFor="priority-relevance" className="flex items-center gap-3 cursor-pointer p-3 rounded-lg hover:bg-background/50 transition-colors border border-transparent hover:border-border">
            <input 
              id="priority-relevance"
              type="radio" 
              name="priority"
              checked={recommendationSettings.prioritize === "relevance"}
              onChange={() => handleRadio("relevance")}
              className="w-4 h-4 accent-primary"
            />
            <span className="flex flex-col">
              <span className="font-medium text-foreground">Relevance First</span>
              <span className="text-sm text-muted-foreground">Prioritize semantic similarity to what you read.</span>
            </span>
          </label>
          
          {/* eslint-disable-next-line jsx-a11y/label-has-associated-control */}
          <label htmlFor="priority-balanced" className="flex items-center gap-3 cursor-pointer p-3 rounded-lg hover:bg-background/50 transition-colors border border-transparent hover:border-border">
            <input 
              id="priority-balanced"
              type="radio" 
              name="priority"
              checked={recommendationSettings.prioritize === "balanced"}
              onChange={() => handleRadio("balanced")}
              className="w-4 h-4 accent-primary"
            />
            <span className="flex flex-col">
              <span className="font-medium text-foreground">Balanced</span>
              <span className="text-sm text-muted-foreground">Mix of relevance, new topics, and freshness.</span>
            </span>
          </label>
          
          {/* eslint-disable-next-line jsx-a11y/label-has-associated-control */}
          <label htmlFor="priority-freshness" className="flex items-center gap-3 cursor-pointer p-3 rounded-lg hover:bg-background/50 transition-colors border border-transparent hover:border-border">
            <input 
              id="priority-freshness"
              type="radio" 
              name="priority"
              checked={recommendationSettings.prioritize === "freshness"}
              onChange={() => handleRadio("freshness")}
              className="w-4 h-4 accent-primary"
            />
            <span className="flex flex-col">
              <span className="font-medium text-foreground">Freshness First</span>
              <span className="text-sm text-muted-foreground">Prioritize breaking and most recent news.</span>
            </span>
          </label>
        </div>
      </section>

      <section className="bg-card border border-border/50 p-6 rounded-2xl">
        <h3 className="text-lg font-bold mb-6">Content Filters</h3>
        <div className="space-y-4">
          {/* eslint-disable-next-line jsx-a11y/label-has-associated-control */}
          <label htmlFor="hideReadArticles" className="flex items-center justify-between cursor-pointer p-3 rounded-lg hover:bg-background/50 transition-colors border border-transparent hover:border-border">
            <span className="flex flex-col">
              <span className="font-medium text-foreground">Hide Read Articles</span>
              <span className="text-sm text-muted-foreground">Do not recommend articles you have already finished.</span>
            </span>
            <input 
              id="hideReadArticles"
              type="checkbox" 
              checked={recommendationSettings.hideReadArticles}
              onChange={() => handleToggle("hideReadArticles")}
              className="w-5 h-5 accent-primary"
            />
          </label>

          {/* eslint-disable-next-line jsx-a11y/label-has-associated-control */}
          <label htmlFor="preferTrustedSources" className="flex items-center justify-between cursor-pointer p-3 rounded-lg hover:bg-background/50 transition-colors border border-transparent hover:border-border">
            <span className="flex flex-col">
              <span className="font-medium text-foreground">Prefer Trusted Sources</span>
              <span className="text-sm text-muted-foreground">Give higher weight to Reuters, AP, and major publishers.</span>
            </span>
            <input 
              id="preferTrustedSources"
              type="checkbox" 
              checked={recommendationSettings.preferTrustedSources}
              onChange={() => handleToggle("preferTrustedSources")}
              className="w-5 h-5 accent-primary"
            />
          </label>

          {/* eslint-disable-next-line jsx-a11y/label-has-associated-control */}
          <label htmlFor="showBreakingNews" className="flex items-center justify-between cursor-pointer p-3 rounded-lg hover:bg-background/50 transition-colors border border-transparent hover:border-border">
            <span className="flex flex-col">
              <span className="font-medium text-foreground">Include Breaking News</span>
              <span className="text-sm text-muted-foreground">Inject global breaking news even if outside your topics.</span>
            </span>
            <input 
              id="showBreakingNews"
              type="checkbox" 
              checked={recommendationSettings.showBreakingNews}
              onChange={() => handleToggle("showBreakingNews")}
              className="w-5 h-5 accent-primary"
            />
          </label>

          {/* eslint-disable-next-line jsx-a11y/label-has-associated-control */}
          <label htmlFor="includeEmergingTopics" className="flex items-center justify-between cursor-pointer p-3 rounded-lg hover:bg-background/50 transition-colors border border-transparent hover:border-border">
            <span className="flex flex-col">
              <span className="font-medium text-foreground">Include Emerging Topics</span>
              <span className="text-sm text-muted-foreground">Discover new trends based on overall network behavior.</span>
            </span>
            <input 
              id="includeEmergingTopics"
              type="checkbox" 
              checked={recommendationSettings.includeEmergingTopics}
              onChange={() => handleToggle("includeEmergingTopics")}
              className="w-5 h-5 accent-primary"
            />
          </label>
        </div>
      </section>
    </div>
  );
}
