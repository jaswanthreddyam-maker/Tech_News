import { m, Variants } from 'framer-motion';
import { WifiOff } from 'lucide-react';
import { useAppReducedMotion } from '@/design-system/accessibility/reducedMotion';
import { RetryButton } from './ErrorState';

interface OfflineStateProps {
  onRetry?: () => void;
  animate?: boolean;
}

export function OfflineState({ onRetry, animate = true }: OfflineStateProps) {
  const shouldReduceMotion = useAppReducedMotion();
  const isAnimated = animate && !shouldReduceMotion;

  const containerVariants: Variants = {
    hidden: { opacity: 0, y: 8 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.2, ease: "easeOut" as const } }
  };

  const Content = (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center max-w-[420px] mx-auto w-full rounded-xl border border-border/50 bg-card/20">
      <div className="w-12 h-12 rounded-full bg-neutral-900/50 flex items-center justify-center mb-4 text-muted-foreground">
        <WifiOff className="w-6 h-6" strokeWidth={1.5} />
      </div>
      <h3 className="text-lg font-bold mb-2 text-foreground">You&apos;re offline.</h3>
      <p className="text-muted-foreground text-sm max-w-sm mx-auto mb-6">
        Showing cached articles.
      </p>
      
      {onRetry && (
        <div className="flex flex-col items-center gap-3 w-full">
          <div className="w-full sm:w-auto">
            <RetryButton onRetry={onRetry} text="Retry" className="bg-primary/10 text-primary hover:bg-primary/20" />
          </div>
        </div>
      )}
    </div>
  );

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
