import { ReactNode } from 'react';
import { m, Variants } from 'framer-motion';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { useAppReducedMotion } from '@/design-system/accessibility/reducedMotion';

interface RetryButtonProps {
  onRetry: () => void;
  text?: string;
  className?: string;
}

export function RetryButton({ onRetry, text = "Try Again", className = "" }: RetryButtonProps) {
  return (
    <button
      onClick={onRetry}
      className={`inline-flex items-center gap-2 px-4 py-2 bg-destructive/10 text-destructive hover:bg-destructive/20 rounded-md font-medium transition-colors text-sm ${className}`}
    >
      <RefreshCw className="w-4 h-4" />
      {text}
    </button>
  );
}

interface ErrorStateProps {
  title?: string;
  description?: string;
  onRetry?: () => void;
  action?: ReactNode;
  className?: string;
  animate?: boolean;
}

export function ErrorState({ 
  title = "Something went wrong", 
  description = "We encountered an unexpected error while loading this content.", 
  onRetry,
  action,
  className = "",
  animate = true
}: ErrorStateProps) {
  const shouldReduceMotion = useAppReducedMotion();
  const isAnimated = animate && !shouldReduceMotion;

  const containerVariants: Variants = {
    hidden: { opacity: 0, y: 8 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.2, ease: "easeOut" as const } }
  };

  const Content = (
    <div 
      role="alert" 
      aria-live="assertive"
      className={`flex flex-col items-center justify-center py-16 px-6 text-center max-w-[420px] mx-auto w-full rounded-xl border border-destructive/20 bg-destructive/5 ${className}`}
    >
      <div className="w-12 h-12 rounded-full bg-destructive/10 flex items-center justify-center mb-4 text-destructive">
        <AlertTriangle className="w-6 h-6" strokeWidth={1.5} />
      </div>
      <h3 className="text-lg font-bold mb-2 text-destructive">{title}</h3>
      <p className="text-muted-foreground text-sm max-w-sm mx-auto mb-6">
        {description}
      </p>
      
      <div className="flex flex-col items-center gap-3 w-full">
        {onRetry && (
          <div className="w-full sm:w-auto">
            <RetryButton onRetry={onRetry} />
          </div>
        )}
        {action && (
          <div className="w-full sm:w-auto">
            {action}
          </div>
        )}
      </div>
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
