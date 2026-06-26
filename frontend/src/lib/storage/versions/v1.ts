export function migrateToV1(state: any, defaultState: any): any {
  // If we have a state, we are migrating from something that lacked schemaVersion
  // but if we are passed null, we are checking for the legacy 'tnt_personalization' key.
  
  if (state) {
    // If we have a state, we just add schemaVersion: 1
    return { ...state, schemaVersion: 1 };
  }

  // Attempt to recover legacy v0 data
  const migrated = { ...defaultState, schemaVersion: 1 };
  try {
    const legacyHistory = localStorage.getItem("tnt_reading_history");
    const legacyBookmarks = localStorage.getItem("tnt_bookmarks");
    const legacySettings = localStorage.getItem("tnt_personalization");

    if (legacyHistory) migrated.readingHistory = JSON.parse(legacyHistory).map((id: number) => ({
      articleId: id, openedAt: Date.now(), completed: false, readingTime: 0
    }));
    if (legacyBookmarks) migrated.bookmarkedArticles = JSON.parse(legacyBookmarks).map((id: number) => ({
      articleId: id, savedAt: Date.now()
    }));
    if (legacySettings) {
      const oldSet = JSON.parse(legacySettings);
      migrated.topicPreferences = (oldSet.topics || []).map((t: string) => ({ topic: t, weight: 100 }));
      if (oldSet.prioritize === "most_relevant") migrated.recommendationSettings.prioritize = "relevance";
      if (oldSet.prioritize === "newest") migrated.recommendationSettings.prioritize = "freshness";
    }

    // Clean up old keys
    localStorage.removeItem("tnt_reading_history");
    localStorage.removeItem("tnt_bookmarks");
    localStorage.removeItem("tnt_personalization");
    
  } catch (e) {
    // eslint-disable-next-line no-console

  }

  return migrated;
}
