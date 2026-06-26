"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { ApiError, ValidationError, NotFoundError, NetworkError, TimeoutError } from "@/lib/api/errors";

export default function ArticleError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {

  }, [error]);

  let title = "Something went wrong";
  let message = "We encountered an unexpected error while loading this article.";
  
  if (error instanceof NotFoundError || error.message.includes("NOT_FOUND")) {
    title = "Article Not Found";
    message = "The article you are looking for doesn't exist or has been removed.";
  } else if (error instanceof ValidationError) {
    title = "Data Validation Error";
    message = "The article data received from the server was malformed or incomplete.";
  } else if (error instanceof NetworkError || error instanceof TimeoutError) {
    title = "Connection Error";
    message = "Failed to reach the server. Please check your internet connection and try again.";
  } else if (error instanceof ApiError) {
    title = `Server Error (${error.status})`;
    message = error.message;
  }

  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center p-4">
      <div className="bg-card border border-destructive/30 p-8 rounded-xl max-w-md w-full text-center space-y-6">
        <div className="mx-auto w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center mb-4">
          <AlertTriangle className="w-6 h-6 text-red-500" />
        </div>
        
        <div className="space-y-2">
          <h2 className="text-xl font-sans font-bold text-foreground tracking-tight">{title}</h2>
          <p className="text-sm text-muted-foreground">{message}</p>
        </div>

        {error instanceof ValidationError && (
          <div className="text-left bg-card p-4 rounded-md border border-border overflow-auto max-h-40">
            <pre className="text-[10px] font-mono text-red-400">
              {JSON.stringify((error as ValidationError).errors, null, 2)}
            </pre>
          </div>
        )}

        <button
          onClick={reset}
          className="w-full flex items-center justify-center gap-2 py-3 px-4 bg-primary text-primary-foreground font-mono text-xs uppercase tracking-widest font-bold hover:bg-primary/90 transition-colors rounded-lg"
        >
          <RefreshCw className="w-4 h-4" />
          Try Again
        </button>
      </div>
    </div>
  );
}
