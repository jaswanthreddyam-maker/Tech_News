// Frozen Event Taxonomy

export type AnalyticsEvent =
  | "Page Viewed"
  | "Article Opened"
  | "Article Completed"
  | "Recommendation Clicked"
  | "Search Executed"
  | "Semantic Search Executed"
  | "Bookmark Added"
  | "Bookmark Removed"
  | "Collection Created"
  | "Notification Opened"
  | "Dashboard Viewed"
  | "Login"
  | "Logout"
  | "Signup"
  | "Theme Changed"
  | "System Error"
  | "Performance Metric";

export interface AnalyticsPayload {
  [key: string]: any;
}
