"use client";

import { openDB, IDBPDatabase } from 'idb';
import { useCallback, useEffect, useRef } from 'react';
import { getApiBaseUrl } from '@/lib/api/getApiBaseUrl';

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

      if (process.env.NEXT_PUBLIC_USE_MOCK_DATA === "true") {
        const clearTx = db.transaction(STORE_NAME, 'readwrite');
        await clearTx.objectStore(STORE_NAME).clear();
        return;
      }

      try {
        // Send to backend
        const response = await fetch(`${getApiBaseUrl()}/behavioral/events`, {
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
      } catch {
        // Network offline or suspended — events remain safely in IndexedDB queue for the next flush
      }
    } catch {
      // IndexedDB access issue
    }
  }, []);

  // Automatically flush queued events when connectivity returns
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const handleOnline = () => {
      import('@/lib/api/anonymousId').then(({ getAnonymousId }) => {
        flush(getAnonymousId());
      });
    };
    window.addEventListener('online', handleOnline);
    return () => window.removeEventListener('online', handleOnline);
  }, [flush]);

  return { enqueue, flush };
}
