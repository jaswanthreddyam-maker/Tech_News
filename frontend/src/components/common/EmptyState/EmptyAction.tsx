import { m, Variants } from 'framer-motion';
import { ReactNode } from 'react';
import { useAppReducedMotion } from '@/design-system/accessibility/reducedMotion';

interface EmptyActionProps {
  primaryAction: ReactNode;
  secondaryAction?: ReactNode;
  animate?: boolean;
}

export function EmptyAction({ primaryAction, secondaryAction, animate = true }: EmptyActionProps) {
  const shouldReduceMotion = useAppReducedMotion();
  const isAnimated = animate && !shouldReduceMotion;

  const variants: Variants = {
    hidden: { opacity: 0, y: 8 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.2, delay: 0.1, ease: "easeOut" } }
  };

  const Content = (
    <div className="flex flex-col items-center gap-3 w-full">
      <div className="w-full sm:w-auto">
        {primaryAction}
      </div>
      {secondaryAction && (
        <div className="text-sm text-muted-foreground/80 hover:text-foreground transition-colors">
          {secondaryAction}
        </div>
      )}
    </div>
  );

  if (isAnimated) {
    return (
      <m.div
        initial="hidden"
        animate="visible"
        variants={variants}
        className="w-full"
      >
        {Content}
      </m.div>
    );
  }

  return <div className="w-full">{Content}</div>;
}
