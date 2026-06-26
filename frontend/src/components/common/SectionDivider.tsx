interface DividerProps {
  className?: string;
}

export function SectionDivider({ className = "" }: DividerProps) {
  return (
    <hr className={`my-12 md:my-16 border-border/50 ${className}`} />
  );
}
