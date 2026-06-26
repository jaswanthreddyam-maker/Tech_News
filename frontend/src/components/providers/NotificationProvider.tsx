"use client";

import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from "react";
import { useAppStore } from "@/store/useStore";

export interface NotificationItem {
  id: string;
  type: "breaking_news" | "system" | "digest";
  title: string;
  message: string;
  url?: string;
  createdAt: number;
  readAt?: number;
}

interface NotificationState {
  notifications: NotificationItem[];
  unreadCount: number;
  isConnected: boolean;
}

interface NotificationContextType extends NotificationState {
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  clearNotification: (id: string) => void;
}

const defaultState: NotificationState = {
  notifications: [],
  unreadCount: 0,
  isConnected: false,
};

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

const API_BASE = typeof window !== "undefined"
  ? (process.env.NEXT_PUBLIC_API_URL || "/api/v1")
  : "";

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<NotificationState>(defaultState);
  const { user } = useAppStore();
  const eventSourceRef = useRef<EventSource | null>(null);

  // Connection logic
  useEffect(() => {
    const isFeatureEnabled = process.env.NEXT_PUBLIC_FF_NOTIFICATIONS === "true";
    if (!user || typeof window === "undefined" || !isFeatureEnabled) return;

    let retryTimeout: NodeJS.Timeout;
    let isUnmounted = false;

    const connectSSE = async () => {
      const url = `${API_BASE}/users/me/notifications/stream`;

      // Pre-flight check to get HTTP status code, as EventSource onerror doesn't expose it
      try {
        const controller = new AbortController();
        const res = await fetch(url, { credentials: "include", signal: controller.signal });
        
        if (res.status === 404 || res.status === 401 || res.status === 403) {
          // eslint-disable-next-line no-console

          controller.abort();
          return; // Stop connecting forever
        }
        // If it's a 200/other transient, abort the fetch and let EventSource handle the actual connection
        controller.abort();
      } catch (err) {
        // Network error, transient. Allow EventSource to try and fail, then retry.
      }

      if (isUnmounted) return;

      const es = new EventSource(url, { withCredentials: true });

      es.onopen = () => {
        setState(prev => ({ ...prev, isConnected: true }));
      };

      es.onmessage = (event) => {
        try {
          const newNotification = JSON.parse(event.data) as NotificationItem;
          setState(prev => {
            const notifications = [newNotification, ...prev.notifications].slice(0, 50); // keep last 50
            return {
              ...prev,
              notifications,
              unreadCount: notifications.filter(n => !n.readAt).length
            };
          });
        } catch (e) {
          // eslint-disable-next-line no-console

        }
      };

      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      es.onerror = (err) => {
        es.close();
        setState(prev => ({ ...prev, isConnected: false }));
        // Auto-reconnect after 5 seconds
        if (!isUnmounted) {
          retryTimeout = setTimeout(connectSSE, 5000);
        }
      };

      eventSourceRef.current = es;
    };

    connectSSE();

    return () => {
      isUnmounted = true;
      clearTimeout(retryTimeout);
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [user]);

  // Load initial notifications (mocked or fetched from backend if needed)
  useEffect(() => {
    const isFeatureEnabled = process.env.NEXT_PUBLIC_FF_NOTIFICATIONS === "true";
    if (!user || !isFeatureEnabled) {
      setState(defaultState);
      return;
    }
    
    // In a real implementation, you might fetch initial unread notifications via REST here
    // before the SSE stream fills in new ones.
    const fetchInitial = async () => {
      try {
        const res = await fetch(`${API_BASE}/users/me/notifications`, {credentials: "include"});
        if (res.ok) {
          const payload = await res.json();
          const items = Array.isArray(payload.data) ? payload.data : [];
          setState(prev => ({
            ...prev,
            notifications: items,
            unreadCount: items.filter((n: NotificationItem) => !n.readAt).length
          }));
        }
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      } catch (e) {
        // Silently fail if endpoint doesn't exist yet
      }
    };
    fetchInitial();
  }, [user]);

  const markAsRead = useCallback((id: string) => {
    setState(prev => {
      const next = prev.notifications.map(n => n.id === id ? { ...n, readAt: Date.now() } : n);
      return { ...prev, notifications: next, unreadCount: next.filter(n => !n.readAt).length };
    });
    // In background, notify server
    fetch(`${API_BASE}/users/me/notifications/${id}/read`, { method: "POST", credentials: "include" }).catch(() => {});
  }, []);

  const markAllAsRead = useCallback(() => {
    setState(prev => {
      const next = prev.notifications.map(n => ({ ...n, readAt: n.readAt || Date.now() }));
      return { ...prev, notifications: next, unreadCount: 0 };
    });
    fetch(`${API_BASE}/users/me/notifications/read`, { method: "POST", credentials: "include" }).catch(() => {});
  }, []);

  const clearNotification = useCallback((id: string) => {
    setState(prev => {
      const next = prev.notifications.filter(n => n.id !== id);
      return { ...prev, notifications: next, unreadCount: next.filter(n => !n.readAt).length };
    });
  }, []);

  return (
    <NotificationContext.Provider value={{ ...state, markAsRead, markAllAsRead, clearNotification }}>
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const context = useContext(NotificationContext);
  if (context === undefined) {
    throw new Error("useNotifications must be used within a NotificationProvider");
  }
  return context;
}
