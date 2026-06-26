import React, { ReactNode } from "react";

export type AsyncResourceState<T> = {
  state: "idle" | "loading" | "success" | "empty" | "error" | "refreshing" | "stale";
  data?: T | null;
  error?: Error | null;
  retry: () => void;
};

interface AsyncResourceProps<T> {
  resource: AsyncResourceState<T>;
  loading: ReactNode;
  empty: ReactNode;
  error: ReactNode;
  children: (data: T) => ReactNode;
}

export function AsyncResource<T>({
  resource,
  loading,
  empty,
  error,
  children,
}: AsyncResourceProps<T>) {
  if (resource.state === "loading" || resource.state === "idle") {
    return <div aria-busy="true">{loading}</div>;
  }

  if (resource.state === "error") {
    return (
      <div aria-live="polite">
        {error}
      </div>
    );
  }

  if (resource.state === "empty") {
    return <>{empty}</>;
  }

  // success, refreshing, stale -> all assume data is present
  if (resource.data !== undefined && resource.data !== null) {
    return <>{children(resource.data)}</>;
  }

  return null;
}
