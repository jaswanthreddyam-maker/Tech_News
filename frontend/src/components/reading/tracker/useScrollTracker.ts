import { useEffect, useRef, useState } from 'react';

const MILESTONES = [10, 25, 50, 75, 90, 100];

export function useScrollTracker(onMilestoneReached: (percent: number) => void) {
  const [maxScroll, setMaxScroll] = useState(0);
  const reportedMilestones = useRef<Set<number>>(new Set());

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleScroll = () => {
      const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
      if (scrollHeight <= 0) return;

      const currentScroll = (window.scrollY / scrollHeight) * 100;
      setMaxScroll(prev => Math.max(prev, currentScroll));
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    for (const milestone of MILESTONES) {
      if (maxScroll >= milestone && !reportedMilestones.current.has(milestone)) {
        reportedMilestones.current.add(milestone);
        onMilestoneReached(milestone);
      }
    }
  }, [maxScroll, onMilestoneReached]);

  return maxScroll;
}
