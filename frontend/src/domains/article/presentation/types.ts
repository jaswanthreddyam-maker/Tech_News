export type AccentColor =
  | "neutral"
  | "breaking"
  | "opinion"
  | "review"
  | "newsletter"
  | "roundup"
  | "live"
  | "explainer";

export type CardVariant =
  | "standard"
  | "collection"
  | "breaking"
  | "review"
  | "opinion"
  | "live";

export type AnimationPreset = "scene" | "breaking" | "card" | "none";
export type InteractionPreset = "standard" | "elevate" | "expand";
export type CardPrimitiveType = "header" | "media" | "topics" | "metadata" | "footer";

export interface BadgeConfig {
  label: string;
  iconName: "newspaper" | "circle-dot" | "layout-grid" | "message-square-quote" | "book-open" | "radio" | "file-text";
  className: string;
}

export interface PresentationMetadataFlags {
  showTopics: boolean;
  showUrgency: boolean;
  showReadingTime: boolean;
  showAuthorByline: boolean;
}

export interface PresentationConfig {
  badge: BadgeConfig;
  accent: AccentColor;
  cardVariant: CardVariant;
  animation: AnimationPreset;
  interaction: InteractionPreset;
  metadata: PresentationMetadataFlags;
}

/**
 * CardVariantDefinition — Executable configuration contract for Card Variants
 */
export interface CardVariantDefinition {
  variant: CardVariant;
  requiredPrimitives: CardPrimitiveType[];
  defaultAccent: AccentColor;
  layoutDescription: string;
  validate: (article: any, config: PresentationConfig) => boolean;
}

export const CARD_VARIANT_DEFINITIONS: Record<CardVariant, CardVariantDefinition> = {
  collection: {
    variant: "collection",
    requiredPrimitives: ["header", "media", "topics", "metadata", "footer"],
    defaultAccent: "newsletter",
    layoutDescription: "Multi-topic collection card showing inline topic chips and section count.",
    validate: (article, config) => {
      const hasTopics = Boolean(article?.primaryTopics?.length || article?.primary_topics?.length);
      return hasTopics && config.metadata.showTopics;
    },
  },
  breaking: {
    variant: "breaking",
    requiredPrimitives: ["header", "media", "metadata", "footer"],
    defaultAccent: "breaking",
    layoutDescription: "High-urgency card featuring pulsing red indicator and timestamp priority.",
    validate: (_, config) => config.metadata.showUrgency && config.accent === "breaking",
  },
  review: {
    variant: "review",
    requiredPrimitives: ["header", "media", "metadata", "footer"],
    defaultAccent: "review",
    layoutDescription: "Product evaluation card with verdict badge and cyan accent styling.",
    validate: (_, config) => config.cardVariant === "review",
  },
  opinion: {
    variant: "opinion",
    requiredPrimitives: ["header", "media", "metadata", "footer"],
    defaultAccent: "opinion",
    layoutDescription: "Author-first editorial card emphasizing byline and warm amber styling.",
    validate: (_, config) => config.metadata.showAuthorByline,
  },
  live: {
    variant: "live",
    requiredPrimitives: ["header", "media", "metadata", "footer"],
    defaultAccent: "live",
    layoutDescription: "Real-time update card with emerald live pulse and timestamp counter.",
    validate: (_, config) => config.metadata.showUrgency,
  },
  standard: {
    variant: "standard",
    requiredPrimitives: ["header", "media", "metadata", "footer"],
    defaultAccent: "neutral",
    layoutDescription: "Clean fallback editorial story card.",
    validate: () => true,
  },
};
