'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';

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
        
        const url = new URL('/api/v1/behavioral/sessions', window.location.origin);
        url.searchParams.append('status', 'in_progress');
        url.searchParams.append('limit', '3');
        if (anonId) {
          url.searchParams.append('anonymous_id', anonId);
        }
        
        const res = await fetch(url.toString());
        if (res.ok) {
          const data = await res.json();
          setSessions(data);
        }
      } catch (err) {
        console.error('Failed to fetch resume reading sessions:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchSessions();
  }, []);

  if (loading || sessions.length === 0) return null;

  return (
    <div className="space-y-4 mb-8">
      <h2 className="text-xl font-semibold tracking-tight">Resume Reading</h2>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {sessions.map((session) => (
          <Card key={session.session_id} className="hover:bg-muted/50 transition-colors">
            <CardHeader className="pb-2">
              <CardTitle className="text-base leading-tight line-clamp-2">
                <Link href={`/articles/${session.article_slug}`} className="hover:underline before:absolute before:inset-0">
                  {session.article_title || 'Untitled Article'}
                </Link>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 text-sm text-muted-foreground relative z-10">
                <div className="flex justify-between">
                  <span>{session.completion_percentage}% completed</span>
                  <span>{Math.max(1, Math.round(session.total_reading_seconds / 60))} min read</span>
                </div>
                <Progress value={session.completion_percentage} className="h-2" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
