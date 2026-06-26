import { Suspense } from "react";
import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { getLatestNews, getTrendingArticles, getArticles, getBreakingNews } from "@/lib/api/articles";
import {
  HeroSection,
  BreakingNews,
  AIHighlights,
  TrendingStories,
  LatestNews,
  RelatedStories,
  ExploreTopics,
  PopularSources,
  Newsletter,
  StoryEvolution,
} from "@/components/homepage";
import { ResumeReading } from "@/components/reading/ResumeReading";
import { SectionErrorBoundary } from "@/components/ui/SectionErrorBoundary";
import { Container } from "@/components/layout/Container";
import { Skeleton } from "@/components/ui/skeleton";

export const metadata = {
  title: "Tech News Today | Autonomous AI Newsroom",
  description: "AI-powered real-time technology news portal. Discover emerging innovations in Artificial Intelligence, Robotics, and Startups.",
  openGraph: {
    title: "Tech News Today | AI Newsroom",
    description: "AI-powered real-time technology news portal.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Tech News Today",
    description: "AI-powered real-time technology news portal.",
  },
  alternates: {
    canonical: "https://technewstoday.com",
  }
};

const jsonLd = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "WebSite",
      "@id": "https://technewstoday.com/#website",
      "url": "https://technewstoday.com/",
      "name": "Tech News Today",
      "description": "AI-powered real-time technology news portal.",
      "publisher": {
        "@id": "https://technewstoday.com/#organization"
      },
      "potentialAction": {
        "@type": "SearchAction",
        "target": "https://technewstoday.com/search?q={search_term_string}",
        "query-input": "required name=search_term_string"
      }
    },
    {
      "@type": "Organization",
      "@id": "https://technewstoday.com/#organization",
      "name": "Tech News Today",
      "url": "https://technewstoday.com/",
      "logo": {
        "@type": "ImageObject",
        "url": "https://technewstoday.com/logo.png"
      }
    }
  ]
};

export default async function HomePage() {
  const queryClient = new QueryClient();

  // Prefetch data for the most critical above-the-fold sections
  await Promise.allSettled([
    queryClient.prefetchQuery({
      queryKey: ["articles", "hero"],
      queryFn: () => getArticles({ limit: 1 }),
    }),
    queryClient.prefetchQuery({
      queryKey: ["articles", "trending"],
      queryFn: () => getTrendingArticles(),
    }),
    queryClient.prefetchQuery({
      queryKey: ["articles", "breaking"],
      queryFn: () => getBreakingNews(),
    })
  ]);

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <div className="flex flex-col gap-16 pb-20">
        <h1 className="sr-only">Tech News Today</h1>
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
        
        {/* Above the Fold: Hero & Breaking */}
        <Container size="wide" className="mt-8">
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
            <div className="lg:col-span-3">
              <SectionErrorBoundary fallback={<Skeleton className="w-full h-[500px]" />}>
                <Suspense fallback={<Skeleton className="w-full h-[500px]" />}>
                  <HeroSection />
                </Suspense>
              </SectionErrorBoundary>
            </div>
            <div className="lg:col-span-1">
              <SectionErrorBoundary fallback={<Skeleton className="w-full h-[400px]" />}>
                <Suspense fallback={<Skeleton className="w-full h-[400px]" />}>
                  <AIHighlights />
                </Suspense>
              </SectionErrorBoundary>
            </div>
          </div>
        </Container>

        {/* Resume Reading Section */}
        <Container size="wide">
          <SectionErrorBoundary fallback={<div className="h-0" />}>
            <Suspense fallback={<div className="h-0" />}>
              <ResumeReading />
            </Suspense>
          </SectionErrorBoundary>
        </Container>

        {/* Live Breaking News Ticker / Cards */}
        <Container size="wide">
          <SectionErrorBoundary fallback={<div className="h-[140px]" />}>
            <Suspense fallback={<Skeleton className="w-full h-[140px]" />}>
              <BreakingNews />
            </Suspense>
          </SectionErrorBoundary>
        </Container>

        {/* Trending Stories Grid */}
        <Container>
          <SectionErrorBoundary fallback={<Skeleton className="w-full h-[500px]" />}>
            <Suspense fallback={<Skeleton className="w-full h-[500px]" />}>
              <TrendingStories />
            </Suspense>
          </SectionErrorBoundary>
        </Container>

        {/* Story Evolution (Timeline) */}
        <Container>
          <SectionErrorBoundary fallback={<Skeleton className="w-full h-[300px]" />}>
            <Suspense fallback={<Skeleton className="w-full h-[300px]" />}>
              <StoryEvolution />
            </Suspense>
          </SectionErrorBoundary>
        </Container>

        {/* Latest News & Sidebar */}
        <Container size="wide">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
            <div className="lg:col-span-2 space-y-12">
              <SectionErrorBoundary fallback={<Skeleton className="w-full h-[800px]" />}>
                <Suspense fallback={<Skeleton className="w-full h-[800px]" />}>
                  <LatestNews />
                </Suspense>
              </SectionErrorBoundary>

              <SectionErrorBoundary fallback={<Skeleton className="w-full h-[600px]" />}>
                <Suspense fallback={<Skeleton className="w-full h-[600px]" />}>
                  <RelatedStories />
                </Suspense>
              </SectionErrorBoundary>
            </div>
            
            <aside className="space-y-12">
              <SectionErrorBoundary fallback={<Skeleton className="w-full h-[400px]" />}>
                <Suspense fallback={<Skeleton className="w-full h-[400px]" />}>
                  <PopularSources />
                </Suspense>
              </SectionErrorBoundary>

              <SectionErrorBoundary fallback={<Skeleton className="w-full h-[300px]" />}>
                <Suspense fallback={<Skeleton className="w-full h-[300px]" />}>
                  <ExploreTopics />
                </Suspense>
              </SectionErrorBoundary>
            </aside>
          </div>
        </Container>

        {/* Newsletter Section */}
        <SectionErrorBoundary fallback={<Skeleton className="w-full h-[400px]" />}>
          <Suspense fallback={<Skeleton className="w-full h-[400px]" />}>
            <Newsletter />
          </Suspense>
        </SectionErrorBoundary>
      </div>
    </HydrationBoundary>
  );
}
