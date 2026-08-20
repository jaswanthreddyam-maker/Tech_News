import * as React from "react";
import { Navbar } from "@/components/layout/Navbar";
import { ConditionalFooter } from "@/components/layout/ConditionalFooter";
import { GlobalAssistantWrapper } from "@/components/ai/GlobalAssistantWrapper";

export default function PublicLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="relative flex min-h-screen flex-col bg-background text-foreground">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:top-0 focus:left-0 focus:p-4 focus:bg-background focus:text-foreground focus:z-50 focus:outline-none focus:ring-2 focus:ring-primary">
        Skip to content
      </a>
      <Navbar />
      <main id="main-content" className="flex-1 focus:outline-none" tabIndex={-1}>{children}</main>
      <ConditionalFooter />
      <GlobalAssistantWrapper />
    </div>
  );
}
