import { CanonicalArticle } from "../article";
import { TopicCluster, RankingResult } from "./types";

/**
 * computeTopicSimilarityScore — Explainable multi-factor similarity scorer
 * 
 * Weights & Explanations:
 * - Topic Overlap (40%) -> "Shared topic: [Name]"
 * - Category Match (20%) -> "Same category: [Name]"
 * - Recency Proximity (20%) -> "Published recently"
 * - Document Type Alignment (10%) -> "Matching format: [Type]"
 * - Editorial Baseline (10%)
 */
export function computeTopicSimilarityScore(
  target: CanonicalArticle,
  candidate: CanonicalArticle
): RankingResult {
  if (target.id === candidate.id) {
    return { score: 0, explanations: [] };
  }

  const explanations: string[] = [];

  // 1. Topic Overlap (40%)
  const targetTopics = new Set((target.primaryTopics || []).map((t) => t.toLowerCase().trim()));
  const candidateTopics = (candidate.primaryTopics || []).map((t) => t.toLowerCase().trim());
  let topicScore = 0;

  if (targetTopics.size > 0 && candidateTopics.length > 0) {
    const matched = candidateTopics.filter((t) => targetTopics.has(t));
    if (matched.length > 0) {
      const topicName = target.primaryTopics?.find((t) => t.toLowerCase() === matched[0]) || matched[0];
      explanations.push(`Shared topic: ${topicName}`);
    }
    const union = new Set([...Array.from(targetTopics), ...candidateTopics]).size;
    topicScore = union > 0 ? (matched.length / union) * 40 : 0;
  }

  // 2. Category Match (20%)
  const targetCat = typeof target.category === "string" ? target.category : target.category?.name;
  const candCat = typeof candidate.category === "string" ? candidate.category : candidate.category?.name;
  let categoryScore = 0;
  if (targetCat && candCat && targetCat.toLowerCase() === candCat.toLowerCase()) {
    categoryScore = 20;
    explanations.push(`Same category: ${targetCat}`);
  }

  // 3. Recency Proximity (20%)
  let recencyScore = 10;
  if (target.publishedAt && candidate.publishedAt) {
    const diffHours = Math.abs(
      new Date(target.publishedAt).getTime() - new Date(candidate.publishedAt).getTime()
    ) / (1000 * 60 * 60);
    recencyScore = Math.max(0, 20 - (diffHours / 24) * 2);
    if (diffHours <= 48) {
      explanations.push("Published recently");
    }
  }

  // 4. Document Type Alignment (10%)
  let docScore = 5;
  if (target.documentType && candidate.documentType && target.documentType === candidate.documentType) {
    docScore = 10;
    explanations.push(`Format: ${target.documentType.replace(/_/g, " ")}`);
  }

  // 5. Editorial Baseline (10%)
  const totalScore = Math.round(topicScore + categoryScore + recencyScore + docScore + 10);

  return {
    score: totalScore,
    explanations,
  };
}

/**
 * buildTopicClusters — Aggregates articles into explainable topic clusters
 */
export function buildTopicClusters(articles: CanonicalArticle[]): TopicCluster[] {
  const map = new Map<string, { articles: CanonicalArticle[]; latest: CanonicalArticle }>();

  articles.forEach((art) => {
    const topics = art.primaryTopics || (art.category ? [typeof art.category === "string" ? art.category : art.category.name || "Technology"] : ["Technology"]);
    
    topics.forEach((rawTopic) => {
      const topicName = rawTopic.trim();
      if (!topicName) return;

      const key = topicName.toLowerCase();
      if (!map.has(key)) {
        map.set(key, { articles: [art], latest: art });
      } else {
        const existing = map.get(key)!;
        existing.articles.push(art);
      }
    });
  });

  const clusters: TopicCluster[] = [];

  map.forEach((value, key) => {
    const topicLabel = value.articles[0]?.primaryTopics?.find((t) => t.toLowerCase() === key) || key.replace(/\b\w/g, (c) => c.toUpperCase());
    clusters.push({
      topic: topicLabel,
      slug: encodeURIComponent(key),
      storyCount: value.articles.length,
      latestArticle: value.latest,
      score: value.articles.length * 10,
      explanations: [`${value.articles.length} curated stories covering ${topicLabel}`],
    });
  });

  return clusters.sort((a, b) => b.storyCount - a.storyCount);
}
