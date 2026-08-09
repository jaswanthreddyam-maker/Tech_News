import { Suspense } from "react";
import { getArticles } from "@/lib/api/articles";
import {
  HomepageScene,
  BreakingNews,
  TrendingStories,
  LatestNews,
  RelatedStories,
  Newsletter,
  StoryEvolution,
} from "@/components/homepage";
import { HeroCarouselServer } from "@/components/home/hero/HeroCarouselServer";
import { HeroCarouselSkeleton } from "@/components/home/hero/HeroCarouselSkeleton";
import { mapArticlesToFeatured } from "@/lib/mappers/homepage";
import { ResumeReading } from "@/components/reading/ResumeReading";
import { SPACING } from "@/design-system/tokens";
import { SectionErrorBoundary } from "@/components/ui/SectionErrorBoundary";
import { Container } from "@/components/layout/Container";
import { Skeleton } from "@/components/ui/skeleton";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Tech News Today | Autonomous AI Newsroom",
  description:
    "AI-powered real-time technology news portal. Discover emerging innovations in Artificial Intelligence, Robotics, and Startups.",
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
  },
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
        "@id": "https://technewstoday.com/#organization",
      },
      "potentialAction": {
        "@type": "SearchAction",
        "target": "https://technewstoday.com/search?q={search_term_string}",
        "query-input": "required name=search_term_string",
      },
    },
    {
      "@type": "Organization",
      "@id": "https://technewstoday.com/#organization",
      "name": "Tech News Today",
      "url": "https://technewstoday.com/",
      "logo": {
        "@type": "ImageObject",
        "url": "https://technewstoday.com/logo.png",
      },
    },
  ],
};

export default function HomePage() {
  return (
    <HomepageScene>
      <h1 className="sr-only">Tech News Today</h1>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* Hero Spatial Stage Object */}
      <Container size="wide" className={`mt-2 ${SPACING.SECTION_GAP_XL}`}>
        <SectionErrorBoundary
          fallback={<Skeleton className="w-full h-[500px]" />}
        >
          <Suspense fallback={<HeroCarouselSkeleton />}>
            <HeroCarouselServer />
          </Suspense>
        </SectionErrorBoundary>
      </Container>

      {/* Resume Reading (Your Library) */}
      <Container size="wide" className={SPACING.SECTION_GAP_XL}>
        <SectionErrorBoundary fallback={<div className="h-0" />}>
          <Suspense fallback={<div className="h-0" />}>
            <ResumeReading />
          </Suspense>
        </SectionErrorBoundary>
      </Container>

      {/* Trending Stories */}
      <Container size="wide" className={SPACING.SECTION_GAP_XL}>
        <SectionErrorBoundary
          fallback={<Skeleton className="w-full h-[500px]" />}
        >
          <Suspense fallback={<Skeleton className="w-full h-[500px]" />}>
            <TrendingStories />
          </Suspense>
        </SectionErrorBoundary>
      </Container>

      {/* Story Evolution Timeline */}
      <Container size="wide" className={SPACING.SECTION_GAP_XL}>
        <SectionErrorBoundary
          fallback={<Skeleton className="w-full h-[300px]" />}
        >
          <Suspense fallback={<Skeleton className="w-full h-[300px]" />}>
            <StoryEvolution />
          </Suspense>
        </SectionErrorBoundary>
      </Container>

      {/* Explore by Category */}
      <Container size="wide" className={SPACING.SECTION_GAP_XL}>
        <SectionErrorBoundary
          fallback={<Skeleton className="w-full h-[800px]" />}
        >
          <Suspense fallback={<Skeleton className="w-full h-[800px]" />}>
            <LatestNews />
          </Suspense>
        </SectionErrorBoundary>
      </Container>

      {/* Latest Stories */}
      <Container size="wide" className={SPACING.SECTION_GAP_XL}>
        <SectionErrorBoundary fallback={<div className="h-[140px]" />}>
          <Suspense fallback={<Skeleton className="w-full h-[140px]" />}>
            <BreakingNews />
          </Suspense>
        </SectionErrorBoundary>
      </Container>

      {/* Related Stories Spatial Grid */}
      <Container size="wide" className={SPACING.SECTION_GAP_XL}>
        <SectionErrorBoundary
          fallback={<Skeleton className="w-full h-[600px]" />}
        >
          <Suspense fallback={<Skeleton className="w-full h-[600px]" />}>
            <RelatedStories />
          </Suspense>
        </SectionErrorBoundary>
      </Container>

      {/* Newsletter Spatial Object */}
      <Container size="wide" className={SPACING.SECTION_GAP_L}>
        <SectionErrorBoundary
          fallback={<Skeleton className="w-full h-[400px]" />}
        >
          <Suspense fallback={<Skeleton className="w-full h-[400px]" />}>
            <Newsletter />
          </Suspense>
        </SectionErrorBoundary>
      </Container>
    </HomepageScene>
  );
}
