'use client';

import { useState, useEffect, useCallback } from 'react';
import { apiFetch } from '@/lib/api/client';
import { useAppStore } from '@/store/useStore';

export function useFollowEntity(entityId: string) {
  const [isFollowing, setIsFollowing] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const { user } = useAppStore();

  const checkStatus = useCallback(async () => {
    if (!user) {
      setIsLoading(false);
      return;
    }
    try {
      const entities = await apiFetch<any[]>('/me/following/entities');
      setIsFollowing(entities.some(e => e.id === entityId));
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  }, [user, entityId]);

  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  const toggleFollow = async () => {
    if (!user) return;
    try {
      setIsLoading(true);
      const res = await apiFetch<any>(`/me/following/entities/${entityId}`, { method: 'POST' });
      setIsFollowing(res.active);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  return { isFollowing, toggleFollow, isLoading };
}

export function useFollowTopic(topicName: string) {
  const [isFollowing, setIsFollowing] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const { user } = useAppStore();

  const checkStatus = useCallback(async () => {
    if (!user) {
      setIsLoading(false);
      return;
    }
    try {
      const topics = await apiFetch<any[]>('/me/following/topics');
      setIsFollowing(topics.some(t => t.name === topicName));
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  }, [user, topicName]);

  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  const toggleFollow = async () => {
    if (!user) return;
    try {
      setIsLoading(true);
      const res = await apiFetch<any>(`/me/following/topics/${encodeURIComponent(topicName)}`, { method: 'POST' });
      setIsFollowing(res.active);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  return { isFollowing, toggleFollow, isLoading };
}
