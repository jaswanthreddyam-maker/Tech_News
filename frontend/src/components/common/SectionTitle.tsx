import { ReactNode } from "react";

interface TitleProps {
  title: string;
  subtitle?: string;
  icon?: ReactNode;
  rightAction?: ReactNode;
  className?: string;
}

export function SectionTitle({ title, subtitle, icon, rightAction, className = "" }: TitleProps) {
  return (
    <div className={`flex items-end justify-between mb-6 ${className}`}>
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          {icon && <span className="text-primary">{icon}</span>}
          <h2 className="text-2xl md:text-3xl font-bold tracking-tight">{title}</h2>
        </div>
        {subtitle && (
          <p className="text-muted-foreground">{subtitle}</p>
        )}
      </div>
      {rightAction && (
        <div className="shrink-0 mb-1">
          {rightAction}
        </div>
      )}
    </div>
  );
}


