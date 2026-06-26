"use client";

import React, { Suspense, ReactNode } from "react";
import { SectionErrorBoundary } from "@/components/ui/SectionErrorBoundary";
import { LoadingState } from "./LoadingState";
import { ErrorState } from "./ErrorState";

interface Props {
  children: ReactNode;
  loadingText?: string;
  errorTitle?: string;
  fullHeight?: boolean;
}

export function AsyncBoundary({ children, loadingText = "Loading...", errorTitle = "Failed to load content", fullHeight = false }: Props) {
  return (
    <SectionErrorBoundary 
      fallback={({ error, reset }) => (
        <ErrorState 
          title={errorTitle} 
          description={error.message} 
          onRetry={reset} 
        />
      )}
    >
      <Suspense fallback={<LoadingState text={loadingText} fullHeight={fullHeight} />}>
        {children}
      </Suspense>
    </SectionErrorBoundary>
  );
}
