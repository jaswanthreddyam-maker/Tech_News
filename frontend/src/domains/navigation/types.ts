export type RouteKind = "internal" | "external" | "invalid";

export interface ResolvedArticleRoute {
  kind: RouteKind;
  href: string;
  target?: string;
  rel?: string;
  reason?: string;
}

export interface NavigationTelemetryPayload {
  articleId?: string | number;
  slug?: string | null;
  url?: string | null;
  reason: string;
  component?: string;
}

export interface ArticleClickAnalyticsPayload {
  articleId: string | number;
  slug?: string | null;
  sourceComponent?: string;
  category?: string;
  position?: number;
  homepageSection?: string;
}
