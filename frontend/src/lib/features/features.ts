import { FeatureRegistry } from "./types";

// Hardcoded for now. Could be fetched from backend config or environment variables.
export const defaultFeatures: FeatureRegistry = {
  semanticSearch: true,
  notifications: true,
  recommendations: true,
  collections: true,
  storyTimeline: false,
  experimentalAI: false,
};
