import { ReactNode } from 'react';

interface EmptyStateProps {
  children: ReactNode;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function EmptyState({ children, size = 'md', className = '' }: EmptyStateProps) {
  const sizeClasses = {
    sm: 'py-8 px-4',
    md: 'py-16 px-6',
    lg: 'py-24 px-8'
  };

  return (
    <div className={`flex flex-col items-center justify-center text-center max-w-[420px] mx-auto w-full ${sizeClasses[size]} ${className}`}>
      {children}
    </div>
  );
}
