'use client';

import React from 'react';
import { useFollowEntity, useFollowTopic } from '@/hooks/useFollow';
import { useAppStore } from '@/store/useStore';

interface FollowEntityProps {
  entityId: string;
  className?: string;
}

export const FollowEntityButton: React.FC<FollowEntityProps> = ({ entityId, className = '' }) => {
  const { isFollowing, toggleFollow, isLoading } = useFollowEntity(entityId);
  const { user } = useAppStore();

  if (!user) return null;

  return (
    <button
      onClick={toggleFollow}
      disabled={isLoading}
      className={`px-3 py-1 text-xs font-semibold rounded-full transition-colors border ${
        isFollowing 
          ? 'bg-neutral-800 text-neutral-300 border-neutral-700 hover:bg-neutral-700 hover:text-white' 
          : 'bg-blue-600/10 text-blue-500 border-blue-500/50 hover:bg-blue-600/20 hover:text-blue-400'
      } ${className}`}
    >
      {isFollowing ? 'Following' : 'Follow'}
    </button>
  );
};

interface FollowTopicProps {
  topicName: string;
  className?: string;
}

export const FollowTopicButton: React.FC<FollowTopicProps> = ({ topicName, className = '' }) => {
  const { isFollowing, toggleFollow, isLoading } = useFollowTopic(topicName);
  const { user } = useAppStore();

  if (!user) return null;

  return (
    <button
      onClick={toggleFollow}
      disabled={isLoading}
      className={`px-3 py-1 text-xs font-semibold rounded-full transition-colors border ${
        isFollowing 
          ? 'bg-neutral-800 text-neutral-300 border-neutral-700 hover:bg-neutral-700 hover:text-white' 
          : 'bg-blue-600/10 text-blue-500 border-blue-500/50 hover:bg-blue-600/20 hover:text-blue-400'
      } ${className}`}
    >
      {isFollowing ? 'Following' : 'Follow'}
    </button>
  );
};
