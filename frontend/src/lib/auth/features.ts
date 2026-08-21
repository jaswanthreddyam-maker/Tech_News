export enum FeatureCapability {
  AI_DAILY_BRIEFING = "AI_DAILY_BRIEFING",
  AI_PERSONAL_ASSISTANT = "AI_PERSONAL_ASSISTANT",
  AI_ARTICLE_CHAT = "AI_ARTICLE_CHAT",
  SAVED_ARTICLES = "SAVED_ARTICLES",
  WORKSPACES = "WORKSPACES",
  FOLLOW_TOPIC_ENTITY = "FOLLOW_TOPIC_ENTITY",
  SOURCE_FOLLOWING = "SOURCE_FOLLOWING",
}

export interface FeatureMeta {
  title: string;
  subtitle: string;
  badge: string;
}

export const FEATURE_METADATA: Record<FeatureCapability, FeatureMeta> = {
  [FeatureCapability.AI_DAILY_BRIEFING]: {
    title: "Unlock Your Daily AI Briefing",
    subtitle: "Sign in to customize desk coverage, delivery timezones, and receive autonomous Gemini executive summaries.",
    badge: "AI BRIEFING",
  },
  [FeatureCapability.AI_PERSONAL_ASSISTANT]: {
    title: "Unlock Personal AI Assistant",
    subtitle: "Sign in to ask research questions, query synthesized knowledge graphs, and preserve memory across sessions.",
    badge: "AUTONOMOUS AGENT",
  },
  [FeatureCapability.AI_ARTICLE_CHAT]: {
    title: "Sign in to Chat with this Article",
    subtitle: "Unlock interactive conversational analysis, grounded multi-source comparisons, and live citations.",
    badge: "ARTICLE COPILOT",
  },
  [FeatureCapability.SAVED_ARTICLES]: {
    title: "Sign in to Bookmark Stories",
    subtitle: "Save key breaking articles to your profile and synchronize your reading library seamlessly across devices.",
    badge: "CLOUD SYNC",
  },
  [FeatureCapability.WORKSPACES]: {
    title: "Sign in to Access Workspaces",
    subtitle: "Create private research workspaces, organize synthetic notes, and pin critical technology breakthroughs.",
    badge: "RESEARCH HUB",
  },
  [FeatureCapability.FOLLOW_TOPIC_ENTITY]: {
    title: "Sign in to Personalize Your Feed",
    subtitle: "Follow custom companies, AI researchers, and emerging topics to tailor your intelligence stream.",
    badge: "PERSONALIZATION",
  },
  [FeatureCapability.SOURCE_FOLLOWING]: {
    title: "Sign in to Follow Sources",
    subtitle: "Sign in to follow technology publications, curate your personal feed, and sync followed sources across devices.",
    badge: "SOURCE FOLLOWING",
  },
};
