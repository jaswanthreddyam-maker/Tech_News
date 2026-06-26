/* eslint-disable no-console */
"use client";

import React, { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {

  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
    if (typeof window !== "undefined") {
      window.location.reload();
    }
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-[60vh] flex-col items-center justify-center bg-background p-6 text-center text-foreground">
          <div className="max-w-md border border-neutral-800 bg-neutral-950 p-8 rounded-none md:p-12 shadow-2xl">
            <span className="inline-block px-3 py-1 mb-4 text-xs font-mono tracking-widest uppercase border border-red-500 text-red-500">
              SYSTEM FAULT
            </span>
            <h2 className="font-sans text-2xl font-bold tracking-tight text-white mb-3">
              Application Error Occurred
            </h2>
            <p className="font-mono text-sm text-neutral-400 mb-6 leading-relaxed">
              {this.state.error?.message || "An unexpected error disrupted the render tree."}
            </p>
            <button
              onClick={this.handleReset}
              className="px-6 py-3 font-mono text-xs tracking-wider uppercase bg-white text-black hover:bg-neutral-200 transition-all duration-300"
            >
              Initialize Reboot
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
export default ErrorBoundary;
