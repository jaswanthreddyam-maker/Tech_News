"use client";

import { m, Variants } from 'framer-motion';
import { LucideIcon } from 'lucide-react';
import { useAppReducedMotion } from '@/design-system/accessibility/reducedMotion';
import { useState, useEffect } from 'react';

interface EmptyIllustrationProps {
  icon: LucideIcon;
  title: string;
  description: string;
  animate?: boolean;
}

export function EmptyIllustration({ icon: Icon, title, description, animate = true }: EmptyIllustrationProps) {
  const [isMounted, setIsMounted] = useState(false);
  const shouldReduceMotion = useAppReducedMotion();
  const isAnimated = animate && !shouldReduceMotion;

  useEffect(() => {
    setIsMounted(true);
  }, []);

  const containerVariants: Variants = {
    hidden: { opacity: 0, y: 8 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.2, ease: "easeOut" as const } }
  };

  const Content = (
    <>
      <div className="w-16 h-16 rounded-full bg-neutral-900/50 flex items-center justify-center mb-6 text-muted-foreground mx-auto">
        <Icon className="w-8 h-8" strokeWidth={1.5} />
      </div>
      <h3 className="text-xl font-bold mb-2 text-foreground">{title}</h3>
      <p className="text-sm text-muted-foreground max-w-[320px] mx-auto mb-6">
        {description}
      </p>
    </>
  );

  if (!isMounted) {
    return <div className="w-full">{Content}</div>;
  }

  if (isAnimated) {
    return (
      <m.div
        initial="hidden"
        animate="visible"
        variants={containerVariants}
        className="w-full"
      >
        {Content}
      </m.div>
    );
  }

  return <div className="w-full">{Content}</div>;
}
