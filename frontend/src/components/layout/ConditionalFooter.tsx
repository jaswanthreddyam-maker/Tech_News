"use client";

import { useSelectedLayoutSegment } from "next/navigation";
import { Footer } from "./Footer";

export function ConditionalFooter() {
  const segment = useSelectedLayoutSegment();

  if (segment !== null) {
    return null;
  }

  return <Footer />;
}
