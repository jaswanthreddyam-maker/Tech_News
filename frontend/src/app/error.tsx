"use client";

import { useEffect } from "react";
import { ErrorState } from "@/components/common/ErrorState";
import { useErrorTracking } from "@/components/providers/ErrorProvider";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const { captureException } = useErrorTracking();

  useEffect(() => {
    captureException(error, { route: "boundary:app/error" });
  }, [error, captureException]);

  return (
    <div className="flex h-screen items-center justify-center p-4">
      <ErrorState
        title="Something went wrong"
        description="An unexpected error occurred while loading this page. We've logged the issue and are investigating."
        onRetry={reset}
      />
    </div>
  );
}
