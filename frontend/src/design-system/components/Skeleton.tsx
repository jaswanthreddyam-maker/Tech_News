"use client";

import React from "react";
import { cn } from "@/lib/utils";
import { LoadingStateLevel } from "../hooks/useLoadingState";

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  level?: LoadingStateLevel;
}

export function Skeleton({
  level = "full",
  className,
  ...props
}: SkeletonProps) {
  return (
    <div
      className={cn(
        "rounded-md bg-muted/50 transition-all duration-300",
        level === "hidden" && "opacity-0",
        level === "subtle" && "opacity-50",
        level === "full" && "animate-pulse motion-reduce:animate-none",
        className
      )}
      {...props}
    />
  );
}
