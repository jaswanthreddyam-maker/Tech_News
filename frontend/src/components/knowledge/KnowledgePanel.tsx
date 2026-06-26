import React, { useState, memo } from 'react';
import Link from 'next/link';
import { Building2, User, Box, Tag, Calendar, Link2, ChevronDown, ChevronUp, Brain } from 'lucide-react';
import { cn } from '@/lib/utils';
import { EmptyState, EmptyIllustration } from '@/components/common/EmptyState';

interface KnowledgeEntity {
  id: string;
  name: string;
  type: string;
  confidence: number;
}

interface KnowledgeTopic {
  name: string;
  confidence: number;
}

interface KnowledgeTimelineEvent {
  event_type: string;
  date: string;
  description: string;
  entities: string[];
  confidence: number;
}

interface KnowledgeRelationship {
  source_id: string;
  source_name: string;
  predicate: string;
  target_id: string;
  target_name: string;
  confidence: number;
}

interface KnowledgePanelProps {
  entities?: KnowledgeEntity[];
  topics?: KnowledgeTopic[];
  timeline?: KnowledgeTimelineEvent[];
  relationships?: KnowledgeRelationship[];
}

const CollapsibleCard = memo(function CollapsibleCard({
  title,
  icon: Icon,
  children,
  defaultOpen = true,
}: {
  title: string;
  icon: React.ElementType;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="bg-card border border-border rounded-lg overflow-hidden mb-3">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-3 hover:bg-accent/5 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
        aria-expanded={isOpen}
      >
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4 text-muted-foreground" />
          <span className="font-semibold text-sm text-foreground">{title}</span>
        </div>
        {isOpen
          ? <ChevronUp className="w-4 h-4 text-muted-foreground" />
          : <ChevronDown className="w-4 h-4 text-muted-foreground" />
        }
      </button>
      {isOpen && (
        <div className="p-3 border-t border-border/50">
          {children}
        </div>
      )}
    </div>
  );
});

export const KnowledgePanel = memo(function KnowledgePanel({
  entities = [],
  topics = [],
  timeline = [],
  relationships = [],
}: KnowledgePanelProps) {
  const companies = entities.filter(e => e.type === 'COMPANY' || e.type === 'ORGANIZATION');
  const people = entities.filter(e => e.type === 'PERSON');
  const products = entities.filter(e => e.type === 'PRODUCT' || e.type === 'TECHNOLOGY');

  const predicateMap: Record<string, string> = {
    RELEASED: 'released',
    ACQUIRED: 'acquired',
    PARTNERED_WITH: 'partnered with',
    INVESTED_IN: 'invested in',
    COMPETES_WITH: 'competes with',
    WORKS_FOR: 'works for',
    FOUNDED: 'founded',
  };

  const formatRelationship = (rel: KnowledgeRelationship) => {
    const verb = predicateMap[rel.predicate] ?? rel.predicate.toLowerCase().replace(/_/g, ' ');
    return (
      <span className="text-sm">
        <Link href={`/entities/${rel.source_id}`} className="text-primary hover:underline">
          {rel.source_name}
        </Link>
        <span className="text-muted-foreground mx-1">{verb}</span>
        <Link href={`/entities/${rel.target_id}`} className="text-primary hover:underline">
          {rel.target_name}
        </Link>
        {'.'}
      </span>
    );
  };

  if (!entities.length && !topics.length && !timeline.length && !relationships.length) {
    return (
      <EmptyState size="sm">
        <EmptyIllustration
          icon={Brain}
          title="No extracted insights"
          description="We couldn't extract any entities or topics from this article."
        />
      </EmptyState>
    );
  }

  return (
    <div className="flex flex-col space-y-1" aria-label="Knowledge panel">
      <div className="mb-3">
        <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground font-mono">
          Knowledge
        </h3>
        <div className="h-px bg-border mt-2 w-full" />
      </div>

      {companies.length > 0 && (
        <CollapsibleCard title="Companies" icon={Building2}>
          <ul className="space-y-2">
            {companies.map(c => (
              <li key={c.id}>
                <Link
                  href={`/entities/${c.id}`}
                  className="text-sm text-primary hover:underline block focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring rounded"
                >
                  {c.name}
                </Link>
              </li>
            ))}
          </ul>
        </CollapsibleCard>
      )}

      {people.length > 0 && (
        <CollapsibleCard title="People" icon={User} defaultOpen={false}>
          <ul className="space-y-2">
            {people.map(p => (
              <li key={p.id}>
                <Link
                  href={`/entities/${p.id}`}
                  className="text-sm text-primary hover:underline block focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring rounded"
                >
                  {p.name}
                </Link>
              </li>
            ))}
          </ul>
        </CollapsibleCard>
      )}

      {products.length > 0 && (
        <CollapsibleCard title="Products" icon={Box}>
          <ul className="space-y-2">
            {products.map(p => (
              <li key={p.id}>
                <Link
                  href={`/entities/${p.id}`}
                  className="text-sm text-primary hover:underline block focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring rounded"
                >
                  {p.name}
                </Link>
              </li>
            ))}
          </ul>
        </CollapsibleCard>
      )}

      {topics.length > 0 && (
        <CollapsibleCard title="Topics" icon={Tag}>
          <div className="flex flex-wrap gap-2">
            {topics.map(t => (
              <Link
                key={t.name}
                href={`/topics/${t.name.toLowerCase().replace(/\s+/g, '-')}`}
                className={cn(
                  "text-xs px-2.5 py-1 rounded-full border border-border",
                  "bg-card text-muted-foreground hover:bg-accent/10 hover:text-foreground",
                  "transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
                )}
              >
                {t.name}
              </Link>
            ))}
          </div>
        </CollapsibleCard>
      )}

      {timeline.length > 0 && (
        <CollapsibleCard title="Timeline" icon={Calendar}>
          <div className="relative border-l border-border ml-2 pl-4 py-1 space-y-4">
            {timeline.map((event, i) => (
              <div key={i} className="relative">
                <div className="absolute -left-[21px] top-1.5 w-2 h-2 bg-primary rounded-full" />
                <div className="text-xs text-muted-foreground font-mono mb-1">{event.date}</div>
                <div className="text-sm text-foreground">{event.description}</div>
              </div>
            ))}
          </div>
        </CollapsibleCard>
      )}

      {relationships.length > 0 && (
        <CollapsibleCard title="Relationships" icon={Link2}>
          <ul className="space-y-3">
            {relationships.map((rel, i) => (
              <li key={i} className="flex items-start gap-2">
                <div className="mt-2 flex-shrink-0">
                  <div className="w-1.5 h-1.5 rounded-full bg-border" />
                </div>
                <div>{formatRelationship(rel)}</div>
              </li>
            ))}
          </ul>
        </CollapsibleCard>
      )}
    </div>
  );
});
