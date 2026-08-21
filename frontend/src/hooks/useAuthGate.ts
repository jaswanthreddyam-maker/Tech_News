"use client";

import { useCallback } from "react";
import { useAppStore } from "@/store/useStore";
import { sessionManager } from "@/lib/session/sessionManager";
import { FeatureCapability, FEATURE_METADATA } from "@/lib/auth/features";

export interface RequireAuthOptions {
  returnUrl?: string;
  onAuthenticated?: () => void;
}

export function useAuthGate() {
  const { user, isRestoringSession, authGate, openAuthGate, closeAuthGate } = useAppStore();

  // Valid authenticated state: hydration finished + user object in store + valid token in session
  const isAuthenticated = !isRestoringSession && !!user && (!!sessionManager.getAccessToken() || !!useAppStore.getState().adminToken);

  const requireAuthentication = useCallback(
    (feature: FeatureCapability, options?: RequireAuthOptions): boolean => {
      // During initial hydration, prevent false-positive auth gates
      if (isRestoringSession) {
        return false;
      }

      if (isAuthenticated) {
        if (options?.onAuthenticated) {
          options.onAuthenticated();
        }
        return true;
      }

      // Guest: Launch contextual authentication gate without making any tokenless API request
      const returnUrl = options?.returnUrl || (typeof window !== "undefined" ? window.location.pathname + window.location.search : "/");
      openAuthGate(feature, returnUrl);
      return false;
    },
    [isAuthenticated, isRestoringSession, openAuthGate]
  );

  const canUse = useCallback(
    (_feature: FeatureCapability): boolean => {
      return isAuthenticated;
    },
    [isAuthenticated]
  );

  return {
    isAuthenticated,
    isRestoringSession,
    authGate,
    requireAuthentication,
    canUse,
    openAuthGate,
    closeAuthGate,
    featureMeta: authGate.feature ? FEATURE_METADATA[authGate.feature] : null,
  };
}
