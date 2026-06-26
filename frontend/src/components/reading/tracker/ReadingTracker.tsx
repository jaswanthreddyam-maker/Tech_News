'use client';

import { useEffect, useRef, useCallback } from 'react';
import { useVisibilityTracker } from './useVisibilityTracker';
import { useIdleTracker } from './useIdleTracker';
import { useTimeTracker } from './useTimeTracker';
import { useScrollTracker } from './useScrollTracker';
import { useOfflineQueue, BehavioralEventPayload } from './useOfflineQueue';

function generateUUID() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

function getAnonymousId() {
  if (typeof window === 'undefined') return null;
  let anonId = localStorage.getItem('tnt_anon_id');
  if (!anonId) {
    anonId = generateUUID();
    localStorage.setItem('tnt_anon_id', anonId);
  }
  return anonId;
}

interface ReadingTrackerProps {
  articleId: string;
  contentVersion?: string;
}

export function ReadingTracker({ articleId, contentVersion }: ReadingTrackerProps) {
  const sessionId = useRef(generateUUID());
  const { enqueue, flush } = useOfflineQueue();
  
  const isVisible = useVisibilityTracker();
  const isIdle = useIdleTracker();
  
  const isActive = isVisible && !isIdle;
  const { accumulatedSeconds } = useTimeTracker(isActive);

  const latestScroll = useRef(0);
  const isCompleted = useRef(false);

  const reportHistory = useCallback(() => {
    import('@/lib/api/client').then(({ apiFetch }) => {
      apiFetch('/me/history', {
        method: 'POST',
        body: JSON.stringify({
          article_id: articleId,
          progress: latestScroll.current,
          completed: isCompleted.current,
          reading_time_seconds: accumulatedSeconds
        })
      }).catch(() => {});
    });
  }, [articleId, accumulatedSeconds]);

  const emitEvent = useCallback((eventType: string, scrollPercent?: number) => {
    const event: BehavioralEventPayload = {
      event_id: generateUUID(),
      session_id: sessionId.current,
      article_id: articleId,
      event_type: eventType,
      event_version: 'v1',
      content_version: contentVersion || 'v1',
      scroll_percent: scrollPercent ?? latestScroll.current,
      reading_time_seconds: accumulatedSeconds,
      occurred_at: new Date().toISOString(),
      device_type: /Mobi|Android/i.test(navigator.userAgent) ? 'mobile' : 'desktop',
      referrer: document.referrer,
      source: 'WEB',
    };
    enqueue(event);
  }, [articleId, contentVersion, accumulatedSeconds, enqueue]);

  useScrollTracker((percent) => {
    latestScroll.current = percent;
    if (percent >= 0.9 && !isCompleted.current) {
      isCompleted.current = true;
      reportHistory();
    }
    emitEvent('reading_progress', percent);
  });

  useEffect(() => {
    emitEvent('article_opened');
  }, [emitEvent]);

  useEffect(() => {
    const interval = setInterval(() => {
      emitEvent('reading_time_update');
      flush(getAnonymousId());
      reportHistory();
    }, 15000);
    return () => clearInterval(interval);
  }, [emitEvent, flush, reportHistory]);

  useEffect(() => {
    if (!isVisible) {
      flush(getAnonymousId());
      reportHistory();
    }
  }, [isVisible, flush, reportHistory]);

  useEffect(() => {
    const handleUnload = () => {
      flush(getAnonymousId());
    };
    window.addEventListener('pagehide', handleUnload);
    return () => window.removeEventListener('pagehide', handleUnload);
  }, [flush]);

  return null;
}
