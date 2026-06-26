"use client";
import Link from "next/link";
import { EmptyState, EmptyIllustration, EmptyAction } from "@/components/common/EmptyState";
import { Search } from "lucide-react";

export default function NotFoundPage() {
  return (
    <div className="flex h-[calc(100vh-64px)] items-center justify-center p-4">
      <EmptyState size="lg">
        <EmptyIllustration
          icon={Search}
          title="Page not found"
          description="The page you are looking for doesn't exist or has been moved."
        />
        <EmptyAction
          primaryAction={
            /* eslint-disable-next-line @next/next/no-html-link-for-pages */
            <a 
              href="/"
              className="px-4 py-2 bg-primary text-primary-foreground rounded-full text-sm font-medium hover:bg-primary/90 transition-colors inline-block"
            >
              Go to Homepage
            </a>
          }
        />
      </EmptyState>
    </div>
  );
}
