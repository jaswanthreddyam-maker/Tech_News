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
import { HeroCarousel } from "@/components/home/hero/HeroCarousel";
import { HeroCarouselSkeleton } from "@/components/home/hero/HeroCarouselSkeleton";
import { HeroLcpPreloader } from "@/components/home/hero/HeroLcpPreloader";
import { mapArticlesToFeatured } from "@/lib/mappers/homepage";
import { ResumeReading } from "@/components/reading/ResumeReading";
import { SPACING } from "@/design-system/tokens";
import { SectionErrorBoundary } from "@/components/ui/SectionErrorBoundary";
import { Container } from "@/components/layout/Container";
import {
  TrendingSkeleton,
  CategoryNewsSkeleton,
  StoryEvolutionSkeleton,
  BreakingNewsSkeleton,
  NewsletterSkeleton,
} from "@/components/skeletons";

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

export default async function HomePage() {
  let initialItems: any[] = [];
  try {
    const raw = await getArticles({ limit: 25, sort_by: "trending" });
    const rawArticles = Array.isArray(raw) ? raw : (raw as any)?.data || [];
    initialItems = mapArticlesToFeatured(rawArticles);
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error("Failed server-side fetch of homepage articles:", err);
  }

  return (
    <HomepageScene>
      <h1 className="sr-only">Tech News Today</h1>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* Invisible Server Preloader for LCP Image */}
      <Suspense fallback={null}>
        <HeroLcpPreloader />
      </Suspense>

      {/* Hero Spatial Stage Object */}
      <Container size="wide" className={`mt-2 ${SPACING.SECTION_GAP_XL}`}>
        <SectionErrorBoundary
          fallback={<HeroCarouselSkeleton />}
        >
          <HeroCarousel items={initialItems} />
        </SectionErrorBoundary>
      </Container>

      {/* Resume Reading (Your Library) */}
      <Container size="wide" className={SPACING.SECTION_GAP_M}>
        <SectionErrorBoundary fallback={<div className="h-0" />}>
          <Suspense fallback={<div className="h-0" />}>
            <ResumeReading />
          </Suspense>
        </SectionErrorBoundary>
      </Container>

      {/* Trending Stories */}
      <Container size="wide" className={SPACING.SECTION_GAP_XL}>
        <SectionErrorBoundary
          fallback={<TrendingSkeleton />}
        >
          <Suspense fallback={<TrendingSkeleton />}>
            <TrendingStories />
          </Suspense>
        </SectionErrorBoundary>
      </Container>

      {/* Story Evolution Timeline */}
      <Container size="wide" className={SPACING.SECTION_GAP_XL}>
        <SectionErrorBoundary
          fallback={<StoryEvolutionSkeleton />}
        >
          <Suspense fallback={<StoryEvolutionSkeleton />}>
            <StoryEvolution />
          </Suspense>
        </SectionErrorBoundary>
      </Container>

      {/* Explore by Category */}
      <Container size="wide" className={SPACING.SECTION_GAP_XL}>
        <SectionErrorBoundary
          fallback={<CategoryNewsSkeleton />}
        >
          <Suspense fallback={<CategoryNewsSkeleton />}>
            <LatestNews />
          </Suspense>
        </SectionErrorBoundary>
      </Container>

      {/* Latest Stories */}
      <Container size="wide" className={SPACING.SECTION_GAP_XL}>
        <SectionErrorBoundary fallback={<div className="h-[140px]" />}>
          <Suspense fallback={<BreakingNewsSkeleton />}>
            <BreakingNews />
          </Suspense>
        </SectionErrorBoundary>
      </Container>

      {/* Newsletter Spatial Object */}
      <Container size="wide" className={SPACING.SECTION_GAP_L}>
        <SectionErrorBoundary
          fallback={<NewsletterSkeleton />}
        >
          <Suspense fallback={<NewsletterSkeleton />}>
            <Newsletter />
          </Suspense>
        </SectionErrorBoundary>
      </Container>
    </HomepageScene>
  );
}
