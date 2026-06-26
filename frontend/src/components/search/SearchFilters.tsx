"use client";

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { SearchFilters as ISearchFilters } from "@/lib/api/search/types";

interface Props {
  filters: ISearchFilters;
  onChange: (filters: ISearchFilters) => void;
}

export function SearchFilters({ filters, onChange }: Props) {
  const handleChange = (key: keyof ISearchFilters, value: string) => {
    // Convert 'all' back to undefined for cleaner URL state, except for Match Type where 'hybrid' is default on backend
    const val = value === "all" ? undefined : value;
    onChange({ ...filters, [key]: val });
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-bold mb-3 font-mono tracking-wider uppercase">Match Type</h3>
        <Select value={filters.matchType || "all"} onValueChange={(v: string) => handleChange("matchType", v)}>
          <SelectTrigger>
            <SelectValue placeholder="All" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Modes</SelectItem>
            <SelectItem value="hybrid">Hybrid</SelectItem>
            <SelectItem value="semantic">Semantic</SelectItem>
            <SelectItem value="keyword">Keyword</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div>
        <h3 className="text-sm font-bold mb-3 font-mono tracking-wider uppercase">Sort By</h3>
        <Select value={filters.sort || "relevance"} onValueChange={(v: string) => handleChange("sort", v)}>
          <SelectTrigger>
            <SelectValue placeholder="Relevance" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="relevance">Relevance</SelectItem>
            <SelectItem value="freshness">Freshness</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div>
        <h3 className="text-sm font-bold mb-3 font-mono tracking-wider uppercase">Date Range</h3>
        <Select value={filters.dateRange || "all"} onValueChange={(v: string) => handleChange("dateRange", v)}>
          <SelectTrigger>
            <SelectValue placeholder="Any time" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Any time</SelectItem>
            <SelectItem value="today">Past 24 hours</SelectItem>
            <SelectItem value="week">Past week</SelectItem>
            <SelectItem value="month">Past month</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div>
        <h3 className="text-sm font-bold mb-3 font-mono tracking-wider uppercase">Category</h3>
        <Select value={filters.category || "all"} onValueChange={(v: string) => handleChange("category", v)}>
          <SelectTrigger>
            <SelectValue placeholder="All Categories" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Categories</SelectItem>
            <SelectItem value="artificial-intelligence">Artificial Intelligence</SelectItem>
            <SelectItem value="robotics">Robotics</SelectItem>
            <SelectItem value="startups">Startups</SelectItem>
            <SelectItem value="cybersecurity">Cybersecurity</SelectItem>
            <SelectItem value="software-development">Software Development</SelectItem>
            <SelectItem value="space-science">Space & Science</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div>
        <h3 className="text-sm font-bold mb-3 font-mono tracking-wider uppercase">Credibility</h3>
        <Select value={filters.credibility?.toString() || "all"} onValueChange={(v: string) => handleChange("credibility", v)}>
          <SelectTrigger>
            <SelectValue placeholder="Any" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Any</SelectItem>
            <SelectItem value="90">High (&gt;90%)</SelectItem>
            <SelectItem value="80">Medium (&gt;80%)</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div>
        <h3 className="text-sm font-bold mb-3 font-mono tracking-wider uppercase">AI Confidence</h3>
        <Select value={filters.aiConfidence?.toString() || "all"} onValueChange={(v: string) => handleChange("aiConfidence", v)}>
          <SelectTrigger>
            <SelectValue placeholder="Any" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Any</SelectItem>
            <SelectItem value="90">High (&gt;90%)</SelectItem>
            <SelectItem value="70">Medium (&gt;70%)</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
