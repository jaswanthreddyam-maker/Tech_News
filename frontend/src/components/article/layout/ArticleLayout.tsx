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

  // Normal, rich editorial mode — article occupies the full width of leftover space
  return (
    <Container size="wide" className="mt-8 mb-20">
      <div className="flex flex-col xl:flex-row gap-8 lg:gap-12 relative xl:ml-12">
        {/* Actions (Floating on Desktop, Sticky Bottom on Mobile) */}
        {actions}

        {/* Main Content Column (expands to occupy full leftover space) */}
        <div className="flex-1 min-w-0 max-w-5xl mx-auto xl:mx-0 w-full">
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
      </div>
    </Container>
  );
}
