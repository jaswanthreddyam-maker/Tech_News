import { ReadingStats } from "./ReadingStats";
import { BookmarkList } from "./BookmarkList";
import { RecommendationSettingsForm } from "./RecommendationSettingsForm";
import { CollectionsList } from "./CollectionsList";
import { SavedSearchesList } from "./SavedSearchesList";

export interface DashboardWidget {
  id: string;
  component: React.ComponentType<{ compact?: boolean }>;
  defaultVisible?: boolean;
}

export const dashboardWidgets: DashboardWidget[] = [
  {
    id: "stats",
    component: ReadingStats,
    defaultVisible: true,
  },
  {
    id: "bookmarks",
    component: BookmarkList as any, // because BookmarkList takes limit
    defaultVisible: true,
  },
  {
    id: "preferences",
    component: RecommendationSettingsForm,
    defaultVisible: true,
  },
  {
    id: "collections",
    component: CollectionsList,
    defaultVisible: true,
  },
  {
    id: "saved_searches",
    component: SavedSearchesList,
    defaultVisible: true,
  }
  // Future widgets: continue_reading, reading_calendar, recommendation_feed
];
