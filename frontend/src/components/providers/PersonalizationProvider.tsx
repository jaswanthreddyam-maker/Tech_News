"use client";

import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from "react";
import { CONFIG } from "@/config/constants";
import { loadAndMigrateStorage } from "@/lib/storage/migrator";
import { useAppStore } from "@/store/useStore";
import { PersonalizationSync } from "@/lib/sync/personalizationSync";

export interface ReadingHistoryItem {
  articleId: number;
  slug: string;
  title: string;
  source: string;
  openedAt: number;
  lastReadAt: number;
  completed: boolean;
  readingTime: number; // in seconds
}

export interface SearchHistoryItem {
  query: string;
  searchedAt: number;
  resultCount?: number;
}

export interface TopicPreference {
  topic: string;
  weight: number;
}

export interface SavedSearch {
  query: string;
  filters?: Record<string, any>;
  savedAt: number;
  lastUsedAt: number;
}

export interface Collection {
  id: string;
  name: string;
  color?: string;
  createdAt: number;
}

export interface BookmarkItem {
  articleId: number;
  savedAt: number;
  collectionId?: string;
}

export interface RecommendationSettings {
  prioritize: "relevance" | "freshness" | "balanced";
  hideReadArticles: boolean;
  preferTrustedSources: boolean;
  showBreakingNews: boolean;
  includeEmergingTopics: boolean;
}

export interface PersonalizationState {
  readingHistory: ReadingHistoryItem[];
  bookmarkedArticles: BookmarkItem[];
  collections: Collection[];
  hiddenArticles: number[];
  searchHistory: SearchHistoryItem[];
  savedSearches: SavedSearch[];
  topicPreferences: TopicPreference[];
  recommendationSettings: RecommendationSettings;
  schemaVersion: 2;
}

export type PersonalizationSnapshot = Omit<PersonalizationState, "schemaVersion"> & { schemaVersion?: number; lastSyncedAt?: number };

const defaultState: PersonalizationState = {
  readingHistory: [],
  bookmarkedArticles: [],
  collections: [],
  hiddenArticles: [],
  searchHistory: [],
  savedSearches: [],
  topicPreferences: [],
  recommendationSettings: {
    prioritize: "balanced",
    hideReadArticles: false,
    preferTrustedSources: true,
    showBreakingNews: true,
    includeEmergingTopics: true,
  },
  schemaVersion: 2,
};

interface PersonalizationContextType extends PersonalizationState {
  // Methods for Reading History
  addReadArticle: (article: Omit<ReadingHistoryItem, "openedAt" | "lastReadAt" | "completed" | "readingTime">) => void;
  updateReadTime: (articleId: number, additionalSeconds: number, completed: boolean) => void;
  clearHistory: () => void;
  
  // Methods for Bookmarks
  toggleBookmark: (articleId: number, collectionId?: string) => void;
  
  // Methods for Search History
  addSearchRecord: (query: string, resultCount?: number) => void;

  // Methods for Settings
  updateSettings: (newSettings: Partial<RecommendationSettings>) => void;
  updateTopicPreferences: (topics: TopicPreference[]) => void;
}

const PersonalizationContext = createContext<PersonalizationContextType | undefined>(undefined);

const EXPIRY_MS = CONFIG.READING_EXPIRY_DAYS * 24 * 60 * 60 * 1000;

export function PersonalizationProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<PersonalizationState>(defaultState);
  const [isLoaded, setIsLoaded] = useState(false);
  const { user } = useAppStore();
  
  // Use a ref to always have the latest state for the sync engine
  const stateRef = useRef<PersonalizationState>(state);
  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  // Load state and run migrations on mount
  useEffect(() => {
    const loadState = () => {
      try {
        const migrated = loadAndMigrateStorage(CONFIG.PERSONALIZATION_STORE_KEY, defaultState);
        
        // Clean expired reading history
        const now = Date.now();
        const validHistory = migrated.readingHistory.filter((item: ReadingHistoryItem) => now - item.lastReadAt < EXPIRY_MS);
        if (validHistory.length !== migrated.readingHistory.length) {
          migrated.readingHistory = validHistory;
        }

        setState(migrated as PersonalizationState);
      } catch (e) {
        // eslint-disable-next-line no-console

      } finally {
        setIsLoaded(true);
      }
    };
    
    loadState();
  }, []);

  // Save to localstorage whenever state changes (after load)
  useEffect(() => {
    if (isLoaded) {
      localStorage.setItem(CONFIG.PERSONALIZATION_STORE_KEY, JSON.stringify(state));
    }
  }, [state, isLoaded]);

  // Handle Sync on Auth State changes (Login)
  useEffect(() => {
    if (isLoaded && user) {
      // Trigger a sync when a user logs in
      PersonalizationSync.sync(stateRef.current).then(merged => {
        setState(merged as PersonalizationState);
      });
    }
  }, [isLoaded, user]);

  // Periodic Background Sync
  useEffect(() => {
    if (isLoaded && user) {
      PersonalizationSync.startPeriodicSync(
        () => stateRef.current,
        (merged) => setState(merged as PersonalizationState)
      );
      return () => PersonalizationSync.stopPeriodicSync();
    }
  }, [isLoaded, user]);

  const addReadArticle = useCallback((article: Omit<ReadingHistoryItem, "openedAt" | "lastReadAt" | "completed" | "readingTime">) => {
    setState(prev => {
      const now = Date.now();
      // Remove duplicate if it exists (so we can move it to the front)
      const existing = prev.readingHistory.find(item => item.articleId === article.articleId);
      const filtered = prev.readingHistory.filter(item => item.articleId !== article.articleId);
      
      const newItem: ReadingHistoryItem = {
        ...article,
        openedAt: existing ? existing.openedAt : now,
        lastReadAt: now,
        readingTime: existing ? existing.readingTime : 0,
        completed: existing ? existing.completed : false,
      };

      // Add to front, slice to max
      const nextHistory = [newItem, ...filtered].slice(0, CONFIG.MAX_READING_HISTORY);
      return { ...prev, readingHistory: nextHistory };
    });
  }, []);

  const updateReadTime = useCallback((articleId: number, additionalSeconds: number, completed: boolean) => {
    setState(prev => {
      const nextHistory = prev.readingHistory.map(item => {
        if (item.articleId === articleId) {
          return {
            ...item,
            lastReadAt: Date.now(),
            readingTime: item.readingTime + additionalSeconds,
            completed: item.completed || completed,
          };
        }
        return item;
      });
      return { ...prev, readingHistory: nextHistory };
    });
  }, []);

  const clearHistory = useCallback(() => {
    setState(prev => ({ ...prev, readingHistory: [] }));
  }, []);

  const toggleBookmark = useCallback((articleId: number, collectionId?: string) => {
    setState(prev => {
      const isBookmarked = prev.bookmarkedArticles.some(b => b.articleId === articleId);
      const nextBookmarks = isBookmarked 
        ? prev.bookmarkedArticles.filter(b => b.articleId !== articleId)
        : [{ articleId, savedAt: Date.now(), collectionId }, ...prev.bookmarkedArticles];
      
      return { ...prev, bookmarkedArticles: nextBookmarks.slice(0, CONFIG.MAX_BOOKMARKS) };
    });
  }, []);

  const addSearchRecord = useCallback((query: string, resultCount?: number) => {
    setState(prev => {
      const now = Date.now();
      const filtered = prev.searchHistory.filter(s => s.query.toLowerCase() !== query.toLowerCase());
      const nextSearch = [{ query, searchedAt: now, resultCount }, ...filtered].slice(0, CONFIG.SEARCH_HISTORY_LIMIT);
      return { ...prev, searchHistory: nextSearch };
    });
  }, []);

  const updateSettings = useCallback((newSettings: Partial<RecommendationSettings>) => {
    setState(prev => ({
      ...prev,
      recommendationSettings: { ...prev.recommendationSettings, ...newSettings }
    }));
  }, []);

  const updateTopicPreferences = useCallback((topics: TopicPreference[]) => {
    setState(prev => ({ ...prev, topicPreferences: topics }));
  }, []);



  return (
    <PersonalizationContext.Provider value={{
      ...state,
      addReadArticle,
      updateReadTime,
      clearHistory,
      toggleBookmark,
      addSearchRecord,
      updateSettings,
      updateTopicPreferences
    }}>
      {children}
    </PersonalizationContext.Provider>
  );
}

export function usePersonalization() {
  const context = useContext(PersonalizationContext);
  if (context === undefined) {
    throw new Error("usePersonalization must be used within a PersonalizationProvider");
  }
  return context;
}
