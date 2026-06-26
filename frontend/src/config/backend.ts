/**
 * Backend Capabilities Registry
 * 
 * Centralizes flags for backend features. As the backend evolves (e.g. from v1.0.0 to v1.0.1+),
 * update these flags instead of scattering assumptions throughout the codebase.
 */

export const BackendCapabilities = {
  // Authentication & Identity
  oauth: true,
  sessionManagement: true,
  
  // Features
  notifications: "sse" as "sse" | "websocket" | "polling" | false,
  semanticSearch: true,
  recommendations: true,
  
  // Sync & Storage
  personalizationSync: true,
  
  // Future Capabilities
  storyTimeline: false,
  collaborativeEditing: false,
};
