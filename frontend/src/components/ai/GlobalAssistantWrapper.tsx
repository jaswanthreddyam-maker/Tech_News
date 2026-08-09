"use client";

import nextDynamic from "next/dynamic";

const GlobalAssistant = nextDynamic(
  () => import("./GlobalAssistant").then((m) => m.GlobalAssistant),
  { ssr: false }
);

export function GlobalAssistantWrapper() {
  return <GlobalAssistant />;
}
