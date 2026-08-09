export interface FeedArticle {
  id: number;
  title: string;
  slug?: string;
  url?: string;
  summary?: string;
  description?: string;
  category?: string | { name?: string };
  source?: string;
  source_domain?: string;
  image_url?: string;
  thumbnail_url?: string;
  image?: string;
  read_time?: number;
  published_at?: string;
  reason?: string;
}

export interface FeedResponseItem {
  strategy?: string;
  reason?: string;
  article?: FeedArticle;
  id?: number;
  title?: string;
  slug?: string;
  summary?: string;
  description?: string;
  category?: string | { name?: string };
  source?: string;
  source_domain?: string;
  image_url?: string;
  thumbnail_url?: string;
  read_time?: number;
  url?: string;
}

export interface StoryCardProps {
  article: FeedArticle;
  onClick: () => void;
}
