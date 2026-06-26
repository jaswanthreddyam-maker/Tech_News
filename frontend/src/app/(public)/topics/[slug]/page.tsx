import { notFound } from "next/navigation";
import { apiFetch } from "@/lib/api/client";
import { Container } from "@/components/layout/Container";
import Link from "next/link";
import { Tag, Activity, Clock, TrendingUp } from "lucide-react";
import { FollowTopicButton } from "@/components/ui/FollowButton";

export default async function TopicPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  
  let topicProfile;
  try {
    const res = await apiFetch<any>(`/topics/${slug}`);
    topicProfile = res.data;
  } catch (e) {
    notFound();
  }

  if (!topicProfile) return notFound();

  return (
    <Container size="default" className="py-12">
      {/* Header */}
      <div className="mb-12 border-b border-neutral-800 pb-8">
        <div className="flex items-center gap-4 mb-4">
          <div className="w-16 h-16 bg-neutral-800 rounded-2xl flex items-center justify-center">
            <Tag className="w-8 h-8 text-neutral-400" />
          </div>
          <div>
            <div className="flex items-center gap-4 mb-1">
              <div className="text-xs font-mono uppercase text-neutral-500 tracking-wider">
                {topicProfile.category || "Topic"}
              </div>
              <FollowTopicButton topicName={topicProfile.name} />
            </div>
            <h1 className="text-4xl font-bold font-mono tracking-tight">{topicProfile.name}</h1>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-12">
          
          {/* Latest Articles */}
          <section>
            <div className="flex items-center justify-between mb-6 border-b border-neutral-800 pb-2">
              <h2 className="text-xl font-bold flex items-center gap-2">
                <Activity className="w-5 h-5 text-blue-500" />
                Topic Coverage
              </h2>
            </div>
            <div className="space-y-6">
              {topicProfile.latest_articles?.map((article: any) => (
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
              {(!topicProfile.latest_articles || topicProfile.latest_articles.length === 0) && (
                <p className="text-neutral-500 italic">No recent coverage for this topic.</p>
              )}
            </div>
          </section>

          {/* Timeline */}
          <section>
            <div className="flex items-center justify-between mb-6 border-b border-neutral-800 pb-2">
              <h2 className="text-xl font-bold flex items-center gap-2">
                <Clock className="w-5 h-5 text-purple-500" />
                Topic Timeline
              </h2>
            </div>
            <div className="relative border-l-2 border-neutral-800 ml-3 space-y-8 py-2">
              {topicProfile.timeline?.map((event: any, idx: number) => (
                <div key={idx} className="relative pl-6">
                  <div className="absolute -left-[9px] top-1.5 w-4 h-4 bg-neutral-900 border-2 border-purple-500 rounded-full" />
                  <div className="text-sm font-mono text-purple-400 mb-1">{event.date}</div>
                  <div className="text-neutral-300">{event.description}</div>
                </div>
              ))}
              {(!topicProfile.timeline || topicProfile.timeline.length === 0) && (
                <p className="text-neutral-500 italic pl-6">No timeline events recorded.</p>
              )}
            </div>
          </section>
        </div>

        {/* Sidebar */}
        <div className="space-y-8">
          
          {/* Trending Entities */}
          {topicProfile.trending_entities?.length > 0 && (
            <div className="bg-neutral-900 p-6 rounded-xl border border-neutral-800">
              <h3 className="text-sm font-bold uppercase tracking-wider text-neutral-500 mb-4 flex items-center gap-2">
                <TrendingUp className="w-4 h-4" />
                Trending Entities
              </h3>
              <ul className="space-y-3">
                {topicProfile.trending_entities.map((e: any) => (
                  <li key={e.id}>
                    <Link href={`/entities/${e.id}`} className="flex items-center gap-2 group">
                      <div className="w-2 h-2 rounded-full bg-blue-500" />
                      <span className="text-sm font-medium group-hover:text-blue-400 transition-colors">
                        {e.name}
                      </span>
                      <span className="text-xs text-neutral-500 ml-auto">{e.type}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}

        </div>
      </div>
    </Container>
  );
}
