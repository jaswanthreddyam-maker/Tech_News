export interface FeaturedArticle {
  id: string;
  slug: string;
  title: string;
  summary: string;
  thumbnail?: string | null;
  source: string;
  publishedAt: string;
  readTime: number;
  category: string;
}

export interface HeroCarouselProps {
  items: FeaturedArticle[];
  editorPicks: FeaturedArticle[];
  latest: FeaturedArticle[];
  aiInsights: FeaturedArticle[];
}

export interface HeroCarouselClientProps {
  items: FeaturedArticle[];
  editorPicks: FeaturedArticle[];
  latest: FeaturedArticle[];
  aiInsights: FeaturedArticle[];
  initialIndex?: number;
  onSlideChange?: (index: number) => void;
  onPrimaryAction?: (article: FeaturedArticle) => void;
  onInsightClick?: (article: FeaturedArticle) => void;
}
