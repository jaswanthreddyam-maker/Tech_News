'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { apiFetch } from '@/lib/api/client';
import { useAppStore } from '@/store/useStore';
import { Sparkles, Calendar, ArrowRight } from 'lucide-react';

interface FeedItem {
  article: any;
  reasoning_metadata: {
    matched_entities: string[];
    matched_topics: string[];
    message: string;
  };
  score: number;
}

export default function FeedClient() {
  const { user } = useAppStore();
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const [loading, setLoading] = useState(true);

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

  if (loading) {
    return <div className="animate-pulse flex flex-col gap-6">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="h-48 bg-neutral-900 rounded-xl border border-neutral-800" />
      ))}
    </div>;
  }

  if (!user) {
    return (
      <div className="text-center py-24 bg-neutral-900/50 rounded-xl border border-neutral-800">
        <Sparkles className="w-12 h-12 text-neutral-600 mx-auto mb-4" />
        <h2 className="text-2xl font-semibold mb-2">Sign in to personalize your feed</h2>
        <p className="text-neutral-400 max-w-md mx-auto">
          Create an account to follow your favorite topics and companies, and get a tailored news experience.
        </p>
      </div>
    );
  }

  if (feed.length === 0) {
    return (
      <div className="text-center py-24 bg-neutral-900/50 rounded-xl border border-neutral-800">
        <Sparkles className="w-12 h-12 text-neutral-600 mx-auto mb-4" />
        <h2 className="text-2xl font-semibold mb-2">Your feed is empty</h2>
        <p className="text-neutral-400 max-w-md mx-auto mb-6">
          Follow topics and entities to start seeing personalized recommendations.
        </p>
        <Link href="/topics" className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-full font-medium transition-colors">
          Explore Topics <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      {feed.map((item, i) => (
        <article key={i} className="group relative bg-neutral-900 rounded-xl border border-neutral-800 overflow-hidden hover:border-neutral-700 transition-colors">
          <div className="p-6">
            <div className="flex items-center gap-3 text-xs mb-4">
              <span className="flex items-center gap-1.5 font-medium text-blue-400 bg-blue-500/10 px-2.5 py-1 rounded-full">
                <Sparkles className="w-3.5 h-3.5" />
                {item.reasoning_metadata.message}
              </span>
              <span className="text-neutral-600">•</span>
              <span className="flex items-center gap-1.5 text-neutral-400 font-mono">
                <Calendar className="w-3.5 h-3.5" />
                {new Date(item.article.published_at).toLocaleDateString()}
              </span>
            </div>
            
            <Link href={`/articles/${item.article.id}`}>
              <h2 className="text-2xl font-bold group-hover:text-blue-400 transition-colors mb-3">
                {item.article.title}
              </h2>
            </Link>
            
            <p className="text-neutral-400 leading-relaxed max-w-4xl line-clamp-2">
              {item.article.summary}
            </p>
          </div>
        </article>
      ))}
    </div>
  );
}
