import * as React from "react";
import { cn } from "@/lib/utils";

interface ContainerProps {
  children: React.ReactNode;
  className?: string;
  /** Use "wide" for full-width dashboards, "default" for content pages */
  size?: "default" | "wide" | "narrow";
}

export function Container({ children, className, size = "default" }: ContainerProps) {
  return (
    <div
      className={cn(
        "mx-auto w-full px-4 md:px-6",
        {
          "max-w-screen-xl": size === "default",
          "max-w-screen-2xl": size === "wide",
          "max-w-screen-md": size === "narrow",
        },
        className
      )}
    >
      {children}
    </div>
  );
}
