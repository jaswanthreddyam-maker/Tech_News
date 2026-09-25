import React from "react";
import { Container } from "@/components/layout/Container";


interface ArticleLayoutProps {
  header: React.ReactNode;
  heroImageNode?: React.ReactNode;
  aiSummary: React.ReactNode;
  sourceCredibility?: React.ReactNode;
  toc: React.ReactNode;
  content: React.ReactNode;
  keyTakeaways?: React.ReactNode;
  askAI: React.ReactNode;
  timeline: React.ReactNode;
  related: React.ReactNode;
  actions: React.ReactNode;
  knowledgePanel?: React.ReactNode;
  navigation?: React.ReactNode;
  focusMode: boolean;
}

export function ArticleLayout({
  header,
  heroImageNode,
  aiSummary,
  toc,
  content,
  keyTakeaways,
  askAI,
  timeline,
  related,
  actions,
  knowledgePanel,
  navigation,
  focusMode,
}: ArticleLayoutProps) {
  // Focus Mode layout: strips away sidebars, floats, and secondary widgets
  if (focusMode) {
    return (
      <Container size="default" className="mt-8 mb-20 animate-fade-in">
        <div className="max-w-[var(--reader-max-width,72ch)] mx-auto w-full">
          {/* Header */}
          <div className="mb-8">{header}</div>

          {/* Hero Image */}
          {heroImageNode && <div className="mb-10">{heroImageNode}</div>}

          {/* AI Summary - Collapsible */}
          <div className="mb-10">{aiSummary}</div>

          {/* Full Article Content */}
          <article className="mb-16">{content}</article>

          {/* Key Takeaways */}
          {keyTakeaways && <div className="mb-16">{keyTakeaways}</div>}

          {/* Footer Navigation */}
          {navigation && <div className="mt-12">{navigation}</div>}
        </div>
      </Container>
    );
  }

  // Normal, rich editorial mode — article centered with balanced wings for floating actions
  return (
    <Container size="wide" className="mt-8 mb-20">
      <div className="flex justify-center gap-6 2xl:gap-8 relative w-full">
        {/* Left Wing: Desktop Floating Actions (Mobile sticky toolbar) */}
        <div className="w-0 xl:w-16 shrink-0">
          {actions}
        </div>

        {/* Center: Main Article Column — Centered */}
        <div className="w-full max-w-4xl min-w-0">
          {/* Header */}
          <div className="mb-8">{header}</div>

          {/* Hero Image — revealed before title in stagger order */}
          {heroImageNode && <div className="mb-10">{heroImageNode}</div>}

          {/* AI Summary (Executive Brief) */}
          <div className="mb-10">{aiSummary}</div>

          {/* In-Article Table of Contents (renders when article has 2+ headings) */}
          {toc && <div className="mb-8 max-w-3xl">{toc}</div>}

          {/* Article Reader Content */}
          <article className="mb-16">{content}</article>

          {/* Key Takeaways */}
          {keyTakeaways && <div className="mb-16">{keyTakeaways}</div>}

          {/* Timeline - Below Key Takeaways */}
          {timeline && <div className="mb-16">{timeline}</div>}

          {/* AI Conversational Search - Below Article */}
          <div className="mb-12">{askAI}</div>

          {/* Explore Related Topics & Related Stories - Below Content (All Viewports) */}
          <div className="mb-12">{related}</div>

          {/* Footer Navigation / Continue Reading */}
          {navigation && <div className="mt-12">{navigation}</div>}
        </div>

        {/* Right Wing: Balanced spacer so the article remains mathematically centered on desktop */}
        <div className="hidden xl:block w-16 shrink-0" aria-hidden="true" />
      </div>
    </Container>
  );
}
