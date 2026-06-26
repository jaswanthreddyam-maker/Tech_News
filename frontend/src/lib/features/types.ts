export type FeatureFlag = 
  | "semanticSearch"
  | "notifications"
  | "recommendations"
  | "collections"
  | "storyTimeline"
  | "experimentalAI";

export type FeatureRegistry = Record<FeatureFlag, boolean>;

export interface FeatureContextType {
  features: FeatureRegistry;
  isFeatureEnabled: (feature: FeatureFlag) => boolean;
}
