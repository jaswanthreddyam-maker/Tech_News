import { notFound } from "next/navigation";
import { apiFetch } from "@/lib/api/client";
import { Container } from "@/components/layout/Container";
import Link from "next/link";
import { Building2, User, Activity, Clock, Box, Link2 } from "lucide-react";
import { FollowEntityButton } from "@/components/ui/FollowButton";

export default async function EntityPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  
  let entityProfile;
  try {
    const res = await apiFetch<any>(`/entities/${id}`);
    entityProfile = res.data;
  } catch (e) {
    notFound();
  }

  if (!entityProfile) return notFound();

  return (
    <Container size="default" className="py-12">
      {/* Header */}
      <div className="mb-12 border-b border-neutral-800 pb-8">
        <div className="flex items-center gap-4 mb-4">
          {entityProfile.type === 'PERSON' ? (
            <div className="w-16 h-16 bg-neutral-800 rounded-full flex items-center justify-center">
              <User className="w-8 h-8 text-neutral-400" />
            </div>
          ) : (
            <div className="w-16 h-16 bg-neutral-800 rounded-xl flex items-center justify-center">
              <Building2 className="w-8 h-8 text-neutral-400" />
            </div>
          )}
          <div>
            <div className="flex items-center gap-4 mb-1">
              <div className="text-xs font-mono uppercase text-neutral-500 tracking-wider">
                {entityProfile.type} Profile
              </div>
              <FollowEntityButton entityId={entityProfile.id} />
            </div>
            <h1 className="text-4xl font-bold font-mono tracking-tight">{entityProfile.name}</h1>
          </div>
        </div>
        {entityProfile.description && (
          <p className="text-lg text-neutral-400 max-w-3xl leading-relaxed">
            {entityProfile.description}
          </p>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-12">
          
          {/* Latest News */}
          <section>
            <div className="flex items-center justify-between mb-6 border-b border-neutral-800 pb-2">
              <h2 className="text-xl font-bold flex items-center gap-2">
                <Activity className="w-5 h-5 text-blue-500" />
                Latest News
              </h2>
            </div>
            <div className="space-y-6">
              {entityProfile.latest_news?.map((article: any) => (
                <div key={article.id} className="group">
                  <Link href={`/articles/${article.id}`}>
                    <h3 className="text-lg font-semibold group-hover:text-blue-400 transition-colors mb-2">
                      {article.title}
                    </h3>
                  </Link>
                  <p className="text-sm text-neutral-400 line-clamp-2 mb-2">{article.summary}</p>
                  <div className="text-xs text-neutral-500 flex items-center gap-2">
                    <span>{article.source}</span>
                    <span>•</span>
                    <span>{new Date(article.published_at).toLocaleDateString()}</span>
                  </div>
                </div>
              ))}
              {entityProfile.latest_news?.length === 0 && (
                <p className="text-neutral-500 italic">No recent news available.</p>
              )}
            </div>
          </section>

          {/* Timeline */}
          <section>
            <div className="flex items-center justify-between mb-6 border-b border-neutral-800 pb-2">
              <h2 className="text-xl font-bold flex items-center gap-2">
                <Clock className="w-5 h-5 text-purple-500" />
                Timeline
              </h2>
            </div>
            <div className="relative border-l-2 border-neutral-800 ml-3 space-y-8 py-2">
              {entityProfile.timeline?.map((event: any, idx: number) => (
                <div key={idx} className="relative pl-6">
                  <div className="absolute -left-[9px] top-1.5 w-4 h-4 bg-neutral-900 border-2 border-purple-500 rounded-full" />
                  <div className="text-sm font-mono text-purple-400 mb-1">{event.date}</div>
                  <div className="text-neutral-300">{event.description}</div>
                  <div className="mt-2 flex gap-2 flex-wrap">
                    <span className="text-xs bg-neutral-800 px-2 py-0.5 rounded text-neutral-400">
                      {event.event_type}
                    </span>
                  </div>
                </div>
              ))}
              {(!entityProfile.timeline || entityProfile.timeline.length === 0) && (
                <p className="text-neutral-500 italic pl-6">No timeline events recorded.</p>
              )}
            </div>
          </section>
        </div>

        {/* Sidebar */}
        <div className="space-y-8">
          
          {/* Stats */}
          <div className="bg-neutral-900 p-6 rounded-xl border border-neutral-800">
            <h3 className="text-sm font-bold uppercase tracking-wider text-neutral-500 mb-4">Entity Overview</h3>
            <div className="space-y-4">
              <div>
                <div className="text-xs text-neutral-500 mb-1">Total Mentions</div>
                <div className="text-2xl font-mono">{entityProfile.stats.mention_count}</div>
              </div>
              {entityProfile.stats.first_seen && (
                <div>
                  <div className="text-xs text-neutral-500 mb-1">First Seen</div>
                  <div className="text-sm">{new Date(entityProfile.stats.first_seen).toLocaleDateString()}</div>
                </div>
              )}
            </div>
          </div>

          {/* Relationships */}
          <div className="bg-neutral-900 p-6 rounded-xl border border-neutral-800">
            <h3 className="text-sm font-bold uppercase tracking-wider text-neutral-500 mb-4 flex items-center gap-2">
              <Link2 className="w-4 h-4" />
              Graph Network
            </h3>
            <ul className="space-y-3">
              {entityProfile.relationships?.map((rel: any, i: number) => (
                <li key={i} className="text-sm border-b border-neutral-800 pb-3 last:border-0 last:pb-0">
                  <Link href={`/entities/${rel.source_id}`} className="text-blue-400 hover:underline">{rel.source_name}</Link>
                  <span className="text-neutral-500 mx-1">{(rel.predicate || "").toLowerCase().replace(/_/g, ' ')}</span>
                  <Link href={`/entities/${rel.target_id}`} className="text-blue-400 hover:underline">{rel.target_name}</Link>
                </li>
              ))}
              {(!entityProfile.relationships || entityProfile.relationships.length === 0) && (
                <li className="text-neutral-500 italic text-sm">No relationships found.</li>
              )}
            </ul>
          </div>

          {/* Related Companies (Graph Neighbors) */}
          {entityProfile.related_companies?.length > 0 && (
            <div className="bg-neutral-900 p-6 rounded-xl border border-neutral-800">
              <h3 className="text-sm font-bold uppercase tracking-wider text-neutral-500 mb-4 flex items-center gap-2">
                <Box className="w-4 h-4" />
                Related Companies
              </h3>
              <div className="flex flex-wrap gap-2">
                {entityProfile.related_companies.map((c: any) => (
                  <Link 
                    key={c.id} 
                    href={`/entities/${c.id}`}
                    className="text-xs bg-neutral-800 text-neutral-300 px-3 py-1.5 rounded-full hover:bg-neutral-700 transition-colors"
                  >
                    {c.name}
                  </Link>
                ))}
              </div>
            </div>
          )}

        </div>
      </div>
    </Container>
  );
}
