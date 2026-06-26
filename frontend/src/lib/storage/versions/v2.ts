// eslint-disable-next-line @typescript-eslint/no-unused-vars
export function migrateToV2(state: any, defaultState: any): any {
  // v2 introduced Collections and SavedSearches explicit typing
  // We need to ensure that the bookmarks have collectionId instead of folder
  
  const migrated = { ...state, schemaVersion: 2 as const };
  
  if (Array.isArray(migrated.bookmarkedArticles)) {
    migrated.bookmarkedArticles = migrated.bookmarkedArticles.map((b: any) => {
      // If it has folder, map it to collectionId
      if (b.folder !== undefined) {
        return {
          articleId: b.articleId,
          savedAt: b.savedAt || Date.now(),
          collectionId: b.folder
        };
      }
      return b;
    });
  }

  // Ensure savedSearches exists (it was missing from v1 PersonalizationState explicitly as a separate list, 
  // or it was searchHistory. We introduce savedSearches here).
  if (!Array.isArray(migrated.savedSearches)) {
    migrated.savedSearches = [];
  }

  // Ensure collections exist
  if (!Array.isArray(migrated.collections)) {
    migrated.collections = [];
  }

  return migrated;
}
