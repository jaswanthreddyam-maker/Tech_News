import { CanonicalArticle } from "../article";

export interface RankingResult {
  score: number;
  explanations: string[];
}

export interface TopicCluster {
  topic: string;
  slug: string;
  storyCount: number;
  latestArticle?: CanonicalArticle | null;
  score: number;
  explanations?: string[];
}

export interface TopicRecommendation {
  cluster: TopicCluster;
  relatedArticles: CanonicalArticle[];
  overlapPercentage: number;
  ranking: RankingResult;
}
