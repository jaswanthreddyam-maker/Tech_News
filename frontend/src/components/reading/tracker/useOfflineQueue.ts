"use client";

import { openDB, IDBPDatabase } from 'idb';
import { useCallback, useEffect, useRef } from 'react';

const DB_NAME = 'tnt-behavioral-db';
const STORE_NAME = 'events-queue';

export interface BehavioralEventPayload {
  event_id: string;
  article_id?: string | number;
  session_id: string;
  event_type: string;
  event_version: string;
  content_version?: string;
  scroll_percent?: number;
  reading_time_seconds?: number;
  occurred_at: string;
  device_type?: string;
  referrer?: string;
  metadata_payload?: Record<string, any>;
  source?: string;
}

export function useOfflineQueue() {
  const dbPromise = useRef<Promise<IDBPDatabase | undefined>>();

  useEffect(() => {
    // Only run in browser
    if (typeof window !== 'undefined') {
      dbPromise.current = openDB(DB_NAME, 1, {
        upgrade(db) {
          db.createObjectStore(STORE_NAME, { keyPath: 'event_id' });
        },
      }).catch(err => {
        console.error('Failed to open IndexedDB:', err);
        return undefined;
      });
    }
  }, []);

  const enqueue = useCallback(async (event: BehavioralEventPayload) => {
    if (!dbPromise.current) return;
    try {
      const db = await dbPromise.current;
      if (db) {
        await db.put(STORE_NAME, event);
      }
    } catch (err) {
      console.error('Failed to enqueue event:', err);
    }
  }, []);

  const flush = useCallback(async (anonymousId: string | null) => {
    if (!dbPromise.current || typeof window === 'undefined' || !navigator.onLine) return;
    try {
      const db = await dbPromise.current;
      if (!db) return;

      const tx = db.transaction(STORE_NAME, 'readwrite');
      const store = tx.objectStore(STORE_NAME);
      const events = await store.getAll();

      if (events.length === 0) return;

      // Send to backend
      const response = await fetch('/api/v1/behavioral/events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          events,
          anonymous_id: anonymousId
        }),
      });

      if (response.ok) {
        // Clear queue
        const clearTx = db.transaction(STORE_NAME, 'readwrite');
        await clearTx.objectStore(STORE_NAME).clear();
      }
    } catch (err) {
      console.error('Failed to flush events:', err);
    }
  }, []);

  return { enqueue, flush };
}
