"use client";

import React, { useState, useEffect } from "react";
import { LazyMotion, domMax } from "framer-motion";

export function AnimationProvider({ children }: { children: React.ReactNode }) {
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  if (!isMounted) {
    return <>{children}</>;
  }

  return (
    <LazyMotion features={domMax} strict>
      {children}
    </LazyMotion>
  );
}
