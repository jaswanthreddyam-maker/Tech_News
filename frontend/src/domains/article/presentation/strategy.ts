import { CanonicalArticle } from "../types";
import { PresentationConfig, CARD_VARIANT_DEFINITIONS } from "./types";

export const DEFAULT_PRESENTATION: PresentationConfig = {
  badge: {
    label: "News",
    iconName: "newspaper",
    className: "text-foreground/80 border-white/10 bg-white/[0.03]",
  },
  accent: "neutral",
  cardVariant: "standard",
  animation: "card",
  interaction: "standard",
  metadata: {
    showTopics: false,
    showUrgency: false,
    showReadingTime: true,
    showAuthorByline: false,
  },
};

const PRESENTATION_REGISTRY: Record<string, PresentationConfig> = {
  newsletter: {
    badge: {
      label: "Weekly Newsletter",
      iconName: "newspaper",
      className: "text-foreground/90 border-white/15 bg-white/[0.05] font-semibold",
    },
    accent: "newsletter",
    cardVariant: "collection",
    animation: "scene",
    interaction: "expand",
    metadata: {
      showTopics: true,
      showUrgency: false,
      showReadingTime: true,
      showAuthorByline: false,
    },
  },
  roundup: {
    badge: {
      label: "Weekly Roundup",
      iconName: "layout-grid",
      className: "text-foreground/90 border-white/15 bg-white/[0.05] font-semibold",
    },
    accent: "roundup",
    cardVariant: "collection",
    animation: "scene",
    interaction: "expand",
    metadata: {
      showTopics: true,
      showUrgency: false,
      showReadingTime: true,
      showAuthorByline: false,
    },
  },
  opinion: {
    badge: {
      label: "Opinion",
      iconName: "message-square-quote",
      className: "text-foreground/90 border-white/15 bg-white/[0.05] font-semibold italic",
    },
    accent: "opinion",
    cardVariant: "opinion",
    animation: "card",
    interaction: "elevate",
    metadata: {
      showTopics: false,
      showUrgency: false,
      showReadingTime: true,
      showAuthorByline: true,
    },
  },
  review: {
    badge: {
      label: "Review",
      iconName: "book-open",
      className: "text-foreground/90 border-white/15 bg-white/[0.05] font-semibold",
    },
    accent: "review",
    cardVariant: "review",
    animation: "card",
    interaction: "elevate",
    metadata: {
      showTopics: false,
      showUrgency: false,
      showReadingTime: true,
      showAuthorByline: false,
    },
  },
  live_blog: {
    badge: {
      label: "Live Blog",
      iconName: "radio",
      className: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10 font-bold",
    },
    accent: "live",
    cardVariant: "live",
    animation: "breaking",
    interaction: "standard",
    metadata: {
      showTopics: false,
      showUrgency: true,
      showReadingTime: false,
      showAuthorByline: false,
    },
  },
  breaking_news: {
    badge: {
      label: "Breaking News",
      iconName: "circle-dot",
      className: "text-rose-400 border-rose-500/30 bg-rose-500/10 font-bold animate-pulse",
    },
    accent: "breaking",
    cardVariant: "breaking",
    animation: "breaking",
    interaction: "elevate",
    metadata: {
      showTopics: false,
      showUrgency: true,
      showReadingTime: true,
      showAuthorByline: false,
    },
  },
  explainer: {
    badge: {
      label: "Explainer",
      iconName: "file-text",
      className: "text-foreground/90 border-white/15 bg-white/[0.05] font-semibold",
    },
    accent: "explainer",
    cardVariant: "standard",
    animation: "card",
    interaction: "standard",
    metadata: {
      showTopics: true,
      showUrgency: false,
      showReadingTime: true,
      showAuthorByline: false,
    },
  },
};

/**
 * getPresentationConfig — Resolves canonical UI PresentationConfig for any given documentType or isMultiTopic flag
 */
export function getPresentationConfig(
  docType?: string | null,
  isMultiTopic?: boolean | null
): PresentationConfig {
  if (!docType) {
    if (isMultiTopic) {
      return PRESENTATION_REGISTRY["roundup"];
    }
    return DEFAULT_PRESENTATION;
  }

  const key = docType.toLowerCase().replace(/[\s-]+/g, "_");
  const found = PRESENTATION_REGISTRY[key];

  if (found) return found;

  // Fallback matchers
  if (key.includes("newsletter")) return PRESENTATION_REGISTRY["newsletter"];
  if (key.includes("roundup")) return PRESENTATION_REGISTRY["roundup"];
  if (key.includes("opinion")) return PRESENTATION_REGISTRY["opinion"];
  if (key.includes("review")) return PRESENTATION_REGISTRY["review"];
  if (key.includes("live")) return PRESENTATION_REGISTRY["live_blog"];
  if (key.includes("breaking")) return PRESENTATION_REGISTRY["breaking_news"];
  if (key.includes("explainer")) return PRESENTATION_REGISTRY["explainer"];

  return {
    ...DEFAULT_PRESENTATION,
    badge: {
      label: docType,
      iconName: "newspaper",
      className: "text-foreground/90 border-white/15 bg-white/[0.05] font-semibold",
    },
  };
}

/**
 * getPresentationForArticle — Canonical helper accepting a CanonicalArticle or DTO directly
 * Ensures UI components never do manual documentType string matching!
 */
export function getPresentationForArticle(
  article: Partial<CanonicalArticle> | null | undefined
): PresentationConfig {
  if (!article) return DEFAULT_PRESENTATION;
  const config = getPresentationConfig(article.documentType, article.isMultiTopic);

  // Executable Contract Validation
  const def = CARD_VARIANT_DEFINITIONS[config.cardVariant];
  if (def && !def.validate(article, config)) {
    // If validation fails (e.g. collection card without topics), fallback to standard variant safely
    return {
      ...config,
      cardVariant: "standard",
      metadata: {
        ...config.metadata,
        showTopics: false,
      },
    };
  }

  return config;
}
