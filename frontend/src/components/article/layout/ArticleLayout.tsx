import React from "react";
import { m, useReducedMotion } from "framer-motion";
import { Container } from "@/components/layout/Container";
import { useNavigationType } from "@/hooks/useNavigationType";
import { DURATION, EASING, REVEAL_DELAYS } from "@/design-system/motion/tokens";


interface ArticleLayoutProps {
  header: React.ReactNode;
  heroImageNode?: React.ReactNode;
  aiSummary: React.ReactNode;
  sourceCredibility: React.ReactNode;
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
  sourceCredibility,
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
  const shouldReduceMotion = useReducedMotion();
  const { isColdLoad } = useNavigationType();

  const sidebarVariants = {
    hidden: { opacity: 0, x: 30 },
    visible: {
      opacity: 1,
      x: 0,
      transition: {
        duration: DURATION.normal,
        ease: EASING.standard as any,
        delay: REVEAL_DELAYS.sidebar,
      },
    },
  };

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

  // Normal, rich editorial mode
  return (
    <Container size="wide" className="mt-8 mb-20">
      <div className="flex flex-col xl:flex-row gap-8 lg:gap-12 relative xl:ml-12">
        {/* Actions (Floating on Desktop, Sticky Bottom on Mobile) */}
        {actions}

        {/* Main Content Column (constrained to 72ch for reading ergonomics) */}
        <div className="flex-1 min-w-0 max-w-[var(--reader-max-width,72ch)] mx-auto xl:mx-0 w-full">
          {/* Header */}
          <div className="mb-8">{header}</div>

          {/* Hero Image — revealed before title in stagger order */}
          {heroImageNode && <div className="mb-10">{heroImageNode}</div>}

          {/* AI Summary (Executive Brief) */}
          <div className="mb-10">{aiSummary}</div>

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

        {/* Right Sticky Sidebar — Article Navigation & Relationships ONLY */}
        <m.aside
          initial={isColdLoad && !shouldReduceMotion ? "hidden" : false}
          animate="visible"
          variants={isColdLoad && !shouldReduceMotion ? sidebarVariants : {}}
          className="hidden xl:block w-[320px] shrink-0"
        >
          <div className="sticky top-24 flex flex-col gap-6">
            {sourceCredibility}
            {toc}
          </div>
        </m.aside>

        {/* Tablet Accordion TOC (Hidden on Desktop) */}
        <div className="xl:hidden w-full max-w-[var(--reader-max-width,72ch)] mx-auto mb-8">{toc}</div>
      </div>
    </Container>
  );
}
