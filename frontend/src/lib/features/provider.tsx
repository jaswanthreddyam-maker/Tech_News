"use client";

import React, { createContext, useContext, useMemo } from "react";
import { FeatureContextType, FeatureFlag, FeatureRegistry } from "./types";
import { defaultFeatures } from "./features";

const FeatureContext = createContext<FeatureContextType | undefined>(undefined);

export function FeatureProvider({ children, overrideFeatures = {} }: { children: React.ReactNode, overrideFeatures?: Partial<FeatureRegistry> }) {
  const features = useMemo(() => {
    return { ...defaultFeatures, ...overrideFeatures };
  }, [overrideFeatures]);

  const isFeatureEnabled = (feature: FeatureFlag) => {
    return features[feature] ?? false;
  };

  return (
    <FeatureContext.Provider value={{ features, isFeatureEnabled }}>
      {children}
    </FeatureContext.Provider>
  );
}

export function useFeatures() {
  const context = useContext(FeatureContext);
  if (!context) {
    // If used outside of provider, fallback to defaults
    return {
      features: defaultFeatures,
      isFeatureEnabled: (feature: FeatureFlag) => defaultFeatures[feature] ?? false
    };
  }
  return context;
}
