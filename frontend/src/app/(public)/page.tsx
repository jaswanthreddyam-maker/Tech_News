import { Suspense } from "react";
import { getArticles } from "@/lib/api/articles";
import {
  BreakingNews,
  TrendingStories,
  LatestNews,
  RelatedStories,
  ExploreTopics,
  PopularSources,
  Newsletter,
  StoryEvolution,
} from "@/components/homepage";
import { HeroCarousel } from "@/components/home/hero/HeroCarousel";
import { HeroCarouselSkeleton } from "@/components/home/hero/HeroCarouselSkeleton";
import { mapArticlesToFeatured } from "@/lib/mappers/homepage";
import { ResumeReading } from "@/components/reading/ResumeReading";
import { SectionErrorBoundary } from "@/components/ui/SectionErrorBoundary";
import { Container } from "@/components/layout/Container";
import { Skeleton } from "@/components/ui/skeleton";

export const dynamic = 'force-dynamic';

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

  // Fetch the Hero articles server side
  let featuredArticlesRaw: any[] = [];
  try {
    const articlesRes = await getArticles({ limit: 5 });
    featuredArticlesRaw = articlesRes?.data || [];
  } catch (error) {
    console.error("Failed to fetch featured articles on server:", error);
  }

  const featuredArticles = mapArticlesToFeatured(featuredArticlesRaw);
  const items = featuredArticles;
  
  console.log("[RUNTIME TRACE] HomePage executing. Items count:", items.length);

  const editorPicks = featuredArticles.slice(1);
  const latest = featuredArticles.slice(1);
  const aiInsights = featuredArticles.slice(1);

  return (
    <>
      <div className="flex flex-col gap-16 pb-20">
        <h1 className="sr-only">Tech News Today</h1>
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
        
        {/* Above the Fold: Hero Carousel */}
        <Container size="wide" className="mt-8">
          <SectionErrorBoundary fallback={<Skeleton className="w-full h-[500px]" />}>
            <Suspense fallback={<HeroCarouselSkeleton />}>
              <HeroCarousel
                items={items}
                editorPicks={editorPicks}
                latest={latest}
                aiInsights={aiInsights}
              />
            </Suspense>
          </SectionErrorBoundary>
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
    </>
  );
}
