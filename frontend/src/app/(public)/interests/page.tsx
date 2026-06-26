'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Lock, UserCircle, Activity } from 'lucide-react';

function getLocalAnonymousId() {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('tnt_anon_id');
}

interface Interest {
  entity_type: string;
  entity_id: string;
  score: number;
  confidence: number;
  last_updated: string;
}

export default function InterestsPage() {
  const [interests, setInterests] = useState<Interest[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchInterests() {
      try {
        const anonId = getLocalAnonymousId();
        const params = new URLSearchParams();
        if (anonId) params.append('anonymous_id', anonId);
        
        const res = await fetch(`/api/v1/behavioral/interests?${params.toString()}`);
        if (!res.ok) throw new Error('Failed to fetch interests');
        
        const data = await res.json();
        setInterests(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    
    fetchInterests();
  }, []);

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl space-y-8">
      
      {/* Header and Trust Indicators */}
      <section className="space-y-4">
        <h1 className="text-4xl font-bold tracking-tight text-white flex items-center gap-3">
          <UserCircle className="w-10 h-10 text-primary" />
          My Interest Profile
        </h1>
        
        <Card className="bg-muted/30 border-muted">
          <CardContent className="p-6 flex items-start gap-4">
            <div className="bg-primary/20 p-3 rounded-full shrink-0">
              <Lock className="w-6 h-6 text-primary" />
            </div>
            <div className="space-y-1">
              <h3 className="font-semibold text-lg text-white">Transparent Personalization</h3>
              <p className="text-muted-foreground leading-relaxed">
                We believe you should own your reading data. The topics below are derived strictly from your reading behavior on TechNews. 
                We use this to improve your recommendations. <strong>No creepy tracking, no third-party data brokers.</strong>
              </p>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Derived Interests */}
      <section>
        <Card className="bg-card/50 border-border backdrop-blur shadow-xl">
          <CardHeader className="border-b border-border/50 pb-6">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <CardTitle className="text-2xl text-white flex items-center gap-2">
                  <Activity className="w-6 h-6 text-primary" />
                  Derived Interests
                </CardTitle>
                <CardDescription>
                  Topics and categories identified from your completed reading sessions
                </CardDescription>
              </div>
              <Badge variant="secondary" className="px-3 py-1 text-sm font-medium">
                {interests.length} Topics Identified
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="pt-6">
            {loading ? (
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="flex flex-col gap-2 p-4 rounded-lg bg-muted/20 animate-pulse">
                    <div className="h-6 w-32 bg-muted/40 rounded"></div>
                    <div className="h-2 w-full bg-muted/40 rounded"></div>
                  </div>
                ))}
              </div>
            ) : interests.length === 0 ? (
              <div className="text-center py-12 px-4 rounded-xl border border-dashed border-border">
                <p className="text-muted-foreground mb-2">We haven&apos;t built your profile yet.</p>
                <p className="text-sm text-muted-foreground">Read a few articles to see your personalized interests appear here.</p>
              </div>
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                {interests.map((interest, idx) => (
                  <div 
                    key={`${interest.entity_type}-${interest.entity_id}-${idx}`}
                    className="flex flex-col gap-3 p-5 rounded-xl border border-border/40 bg-background/50 hover:bg-muted/20 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="text-xs uppercase tracking-wider text-muted-foreground">
                          {interest.entity_type}
                        </Badge>
                        <span className="font-semibold text-white tracking-tight">
                          {interest.entity_id}
                        </span>
                      </div>
                      <span className="text-xs font-mono text-primary font-bold">
                        {Math.round(interest.confidence * 100)}% Conf
                      </span>
                    </div>
                    
                    <div className="space-y-1.5">
                      <div className="flex justify-between text-xs text-muted-foreground">
                        <span>Affinity Score</span>
                        <span>{interest.score.toFixed(1)}</span>
                      </div>
                      <Progress 
                        value={Math.min(100, (interest.score / Math.max(...interests.map(i => i.score))) * 100)} 
                        className="h-1.5"
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </section>

    </div>
  );
}
