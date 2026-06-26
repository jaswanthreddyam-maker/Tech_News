import { Loader2 } from "lucide-react";

interface Props {
  text?: string;
  fullHeight?: boolean;
  className?: string;
}

export function LoadingState({ text = "Loading...", fullHeight = false, className = "" }: Props) {
  return (
    <div className={`flex flex-col items-center justify-center p-8 ${fullHeight ? 'min-h-[50vh]' : 'min-h-[200px]'} ${className}`}>
      <Loader2 className="w-8 h-8 text-primary animate-spin mb-4" />
      {text && (
        <p className="text-sm font-mono tracking-wider uppercase text-muted-foreground animate-pulse">
          {text}
        </p>
      )}
    </div>
  );
}
