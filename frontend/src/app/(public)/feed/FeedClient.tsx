'use client';

import { useEffect, useState, useMemo } from 'react';
import Link from 'next/link';
import { apiFetch } from '@/lib/api/client';
import { useAppStore } from '@/store/useStore';
import { Sparkles, ArrowRight } from 'lucide-react';
import { AdaptiveStoryCard } from '@/components/common/card/AdaptiveStoryCard';
import { EditorialDiscoveryFilter, DiscoveryFilterType } from '@/components/common/filters/EditorialDiscoveryFilter';

interface FeedItem {
  article: any;
  reasoning_metadata?: {
    matched_entities?: string[];
    matched_topics?: string[];
    message?: string;
  };
  score?: number;
}

export default function FeedClient() {
  const { user } = useAppStore();
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState<DiscoveryFilterType>("all");

  useEffect(() => {
    if (!user) {
      setLoading(false);
      return;
    }

    const fetchFeed = async () => {
      try {
        const data = await apiFetch<FeedItem[]>('/me/feed?limit=30');
        setFeed(data);
      } catch (err) {
        console.error('Failed to fetch feed', err);
      } finally {
        setLoading(false);
      }
    };

    fetchFeed();
  }, [user]);

  // Compute filter counts
  const filterCounts = useMemo(() => {
    const counts: Partial<Record<DiscoveryFilterType, number>> = { all: feed.length };
    feed.forEach((item) => {
      const docType = item.article?.document_type?.toLowerCase() || item.article?.documentType?.toLowerCase();
      if (docType) {
        if (docType.includes("breaking")) counts.breaking_news = (counts.breaking_news || 0) + 1;
        else if (docType.includes("newsletter")) counts.newsletter = (counts.newsletter || 0) + 1;
        else if (docType.includes("roundup")) counts.roundup = (counts.roundup || 0) + 1;
        else if (docType.includes("opinion")) counts.opinion = (counts.opinion || 0) + 1;
        else if (docType.includes("review")) counts.review = (counts.review || 0) + 1;
      }
    });
    return counts;
  }, [feed]);

  // Filter feed items by active filter
  const filteredItems = useMemo(() => {
    if (activeFilter === "all") return feed;

    return feed.filter((item) => {
      const docType = (item.article?.document_type || item.article?.documentType || "").toLowerCase();
      if (activeFilter === "breaking_news") return docType.includes("breaking");
      if (activeFilter === "newsletter") return docType.includes("newsletter");
      if (activeFilter === "roundup") return docType.includes("roundup");
      if (activeFilter === "opinion") return docType.includes("opinion");
      if (activeFilter === "review") return docType.includes("review");
      return true;
    });
  }, [feed, activeFilter]);

  if (loading) {
    return (
      <div className="animate-pulse grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="h-64 bg-card/40 rounded-xl border border-border/40" />
        ))}
      </div>
    );
  }

  if (!user) {
    return (
      <div className="text-center py-24 bg-card/40 rounded-2xl border border-border/50 p-8 space-y-4">
        <Sparkles className="w-12 h-12 text-muted-foreground/60 mx-auto" />
        <h2 className="text-2xl font-bold font-serif">Sign in to personalize your feed</h2>
        <p className="text-muted-foreground text-sm max-w-md mx-auto">
          Create an account to follow your favorite topics and companies, and get a tailored news experience.
        </p>
      </div>
    );
  }

  if (feed.length === 0) {
    return (
      <div className="text-center py-24 bg-card/40 rounded-2xl border border-border/50 p-8 space-y-4">
        <Sparkles className="w-12 h-12 text-muted-foreground/60 mx-auto" />
        <h2 className="text-2xl font-bold font-serif">Your feed is empty</h2>
        <p className="text-muted-foreground text-sm max-w-md mx-auto mb-6">
          Follow topics and entities to start seeing personalized recommendations.
        </p>
        <Link
          href="/topics"
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-foreground text-background font-mono text-xs uppercase font-bold rounded-full hover:opacity-90 transition-opacity"
        >
          Explore Topics <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Editorial Discovery Filter Bar */}
      <EditorialDiscoveryFilter
        activeFilter={activeFilter}
        onFilterChange={setActiveFilter}
        filterCounts={filterCounts}
      />

      {/* Adaptive Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredItems.map((item, i) => (
          <AdaptiveStoryCard key={item.article?.id || i} article={item.article} />
        ))}
      </div>
    </div>
  );
}
