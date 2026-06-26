import { apiFetch } from "@/lib/api/client";
import { PersonalizationSnapshot } from "@/components/providers/PersonalizationProvider";
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { CONFIG } from "@/config/constants";
import { sessionManager } from "@/lib/session/sessionManager";

let syncIntervalId: ReturnType<typeof setInterval> | null = null;

export const PersonalizationSync = {
  /**
   * Main sync function that merges local state with server state.
   */
  async sync(localState: PersonalizationSnapshot): Promise<PersonalizationSnapshot> {
    if (!sessionManager.isAuthenticated()) {
      return localState; // Do not sync if not logged in
    }

    try {
      // 1. Download server snapshot
      const response = await apiFetch<{ data?: PersonalizationSnapshot }>("/users/me/personalization", { method: "GET" });
      const serverState = response?.data;

      if (!serverState) {
        // First time syncing, server has no state. Just upload local.
        await this.uploadState(localState);
        return { ...localState, lastSyncedAt: Date.now() };
      }

      // 2. Merge local and server state
      const mergedState = this.mergeStates(localState, serverState);

      // 3. Upload merged snapshot
      await this.uploadState(mergedState);

      // 4. Return merged state to replace local cache
      return { ...mergedState, lastSyncedAt: Date.now() };
    } catch (e: any) {
      // Ignore 404 errors as they just mean the endpoint is not yet implemented
      // or the user has no server-side personalization state yet.
      if (e?.status !== 404) {
        // eslint-disable-next-line no-console

      }
      // Return local state if sync fails
      return localState;
    }
  },

  async uploadState(state: PersonalizationSnapshot): Promise<void> {
    await apiFetch("/users/me/personalization", {
      method: "POST",
      body: JSON.stringify(state)
    });
  },

  /**
   * Timestamps-based merge strategy
   * Newest timestamp wins for individual items.
   */
  mergeStates(local: PersonalizationSnapshot, server: PersonalizationSnapshot): PersonalizationSnapshot {
    return {
      readingHistory: this.mergeArrays(local.readingHistory || [], server.readingHistory || [], "articleId", "lastReadAt"),
      bookmarkedArticles: this.mergeArrays(local.bookmarkedArticles || [], server.bookmarkedArticles || [], "articleId", "savedAt"),
      collections: this.mergeArrays(local.collections || [], server.collections || [], "id", "createdAt"),
      hiddenArticles: Array.from(new Set([...(local.hiddenArticles || []), ...(server.hiddenArticles || [])])),
      searchHistory: this.mergeArrays(local.searchHistory || [], server.searchHistory || [], "query", "searchedAt"),
      savedSearches: this.mergeArrays(local.savedSearches || [], server.savedSearches || [], "query", "savedAt"),
      
      // For preferences and settings, we rely on the overall `lastSyncedAt` to resolve conflicts,
      // or we just prefer server if server is newer, but individual fields lack timestamps.
      // We will prefer the one that was modified most recently if we track global sync time,
      // but without global lastModified per object, we assume server is truth for settings 
      // unless local has an explicit change (which is hard to know). We'll assume the one with newer lastSyncedAt wins.
      topicPreferences: (local.lastSyncedAt || 0) > (server.lastSyncedAt || 0) ? local.topicPreferences : server.topicPreferences,
      recommendationSettings: (local.lastSyncedAt || 0) > (server.lastSyncedAt || 0) ? local.recommendationSettings : server.recommendationSettings,
    };
  },

  mergeArrays<T>(localArr: T[], serverArr: T[], keyField: keyof T, timeField: keyof T): T[] {
    const map = new Map<any, T>();

    // Add server items first
    for (const item of serverArr) {
      map.set(item[keyField], item);
    }

    // Merge local items, overriding if timestamp is newer
    for (const item of localArr) {
      const existing = map.get(item[keyField]);
      if (!existing || (item[timeField] as any) > (existing[timeField] as any)) {
        map.set(item[keyField], item);
      }
    }

    // Sort by timestamp descending
    return Array.from(map.values()).sort((a: any, b: any) => b[timeField] - a[timeField]);
  },

  startPeriodicSync(getState: () => PersonalizationSnapshot, updateState: (state: PersonalizationSnapshot) => void) {
    this.stopPeriodicSync();
    // Sync every 30 minutes
    syncIntervalId = setInterval(async () => {
      if (sessionManager.isAuthenticated()) {
        const merged = await this.sync(getState());
        updateState(merged);
      }
    }, 30 * 60 * 1000);
  },

  stopPeriodicSync() {
    if (syncIntervalId) {
      clearInterval(syncIntervalId);
      syncIntervalId = null;
    }
  }
};
