"use client";

import React, { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children?: ReactNode;
  fallback?: ReactNode | ((props: { error: Error; reset: () => void }) => ReactNode);
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class SectionErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // eslint-disable-next-line no-console

    // Send to Sentry or other telemetry service here
    // Sentry.captureException(error, { extra: errorInfo });
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  public render() {
    if (this.state.hasError && this.state.error) {
      if (typeof this.props.fallback === "function") {
        return this.props.fallback({ error: this.state.error, reset: this.handleReset });
      }
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div className="flex flex-col items-center justify-center p-6 border border-red-500/20 bg-red-500/5 rounded-xl">
          <p className="text-sm font-mono text-red-400 mb-4">Section failed to load.</p>
          <button
            onClick={this.handleReset}
            className="px-4 py-2 text-xs font-mono border border-red-500/50 text-red-400 hover:bg-red-500/10 transition-colors rounded-md"
          >
            Retry
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
