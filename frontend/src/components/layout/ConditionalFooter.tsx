"use client";

import { useSelectedLayoutSegment } from "next/navigation";
import { Footer } from "./Footer";

// Segments where full-screen dedicated UI omits the standard footer
const NO_FOOTER_SEGMENTS = new Set(["chat", "workspaces"]);

export function ConditionalFooter() {
  const segment = useSelectedLayoutSegment();

  if (segment && NO_FOOTER_SEGMENTS.has(segment)) {
    return null;
  }

  return <Footer />;
}
