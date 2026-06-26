"use client";

import { useState, useEffect } from "react";

export type LoadingStateLevel = "hidden" | "subtle" | "full";

export function useLoadingState(isLoading: boolean): LoadingStateLevel {
  const [state, setState] = useState<LoadingStateLevel>("hidden");

  useEffect(() => {
    if (!isLoading) {
      setState("hidden");
      return;
    }

    const t1 = setTimeout(() => setState("subtle"), 150);
    const t2 = setTimeout(() => setState("full"), 500);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, [isLoading]);

  return state;
}
