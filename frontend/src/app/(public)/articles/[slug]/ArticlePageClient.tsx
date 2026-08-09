"use client";

import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  ArticleLayout,
  ArticleHeader,
  ArticleReader,
  ReadingProgress,
  ReadingPreferences,
  AISummaryCard,
  SourceCredibility,
  TableOfContents,
  FloatingActions,
} from "@/components/article";
import { ConversationalSearch } from "@/components/ai/ConversationalSearch";
import { KnowledgePanel } from "@/components/knowledge/KnowledgePanel";
import { apiFetch } from "@/lib/api/client";
import { normalizeCanonicalArticle, CanonicalArticle } from "@/domains/article";
import { ExploreRelatedTopics } from "@/components/article/recommendations/ExploreRelatedTopics";
import { AdaptiveStoryCard } from "@/components/common/card/AdaptiveStoryCard";
import { StickyReadingHeader } from "@/components/article/header/StickyReadingHeader";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { Calendar, Sparkles, Eye, Minimize2, Type } from "lucide-react";
import { m, useReducedMotion, useScroll, useTransform } from "framer-motion";
import { ArticleRevealSection } from "@/components/article/layout/ArticleRevealSection";
import { ProgressiveImage } from "@/components/common/ProgressiveImage";
import { ImageLightbox } from "@/components/common/ImageLightbox";
import { useNavigationType } from "@/hooks/useNavigationType";
import { REVEAL_DELAYS, DURATION, EASING } from "@/design-system/motion/tokens";
import { StaggerContainer, StaggerItem } from "@/components/animations";


export default function ArticlePageClient({ article: rawData }: { article: any }) {
  const router = useRouter();
  const shouldReduceMotion = useReducedMotion();
  const { isColdLoad } = useNavigationType();
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const heroRef = useRef<HTMLDivElement>(null);

  const { scrollY } = useScroll();
  const heroParallax = useTransform(scrollY, [0, 400], [0, 25]);

  // Reading Focus: compact controls bar at scrollY > 200
  const [isReadingMode, setIsReadingMode] = useState(false);
  useEffect(() => {
    const onScroll = () => setIsReadingMode(window.scrollY > 200);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Reader States
  const [focusMode, setFocusMode] = useState(false);
  const [compactMode, setCompactMode] = useState(false);
  const [largeTextMode, setLargeTextMode] = useState(false);

  // Load Preferences from localStorage under 'reader_preferences'
  useEffect(() => {
    const saved = localStorage.getItem("reader_preferences");
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setFocusMode(!!parsed.focusMode);
        setCompactMode(!!parsed.compactMode);
        setLargeTextMode(!!parsed.largeTextMode);
      } catch (e) {}
    }
  }, []);

  const savePreferences = (focus: boolean, compact: boolean, large: boolean) => {
    localStorage.setItem(
      "reader_preferences",
      JSON.stringify({ focusMode: focus, compactMode: compact, largeTextMode: large })
    );
  };

  // Apply compactMode and largeTextMode as CSS variable overrides.
  // This cooperates with ReadingPreferences — both write to document.documentElement.
  // The reading preferences font size/spacing remain as the base; these are overrides.
  useEffect(() => {
    const root = document.documentElement;
    if (largeTextMode) {
      root.style.setProperty("--reader-font-size", "1.25rem"); // 20px baseline boost
      root.style.setProperty("--reader-max-width", "76ch");
    } else {
      // Restore whatever ReadingPreferences last set (re-trigger from storage)
      try {
        const stored = localStorage.getItem("tnt_reading_preferences");
        if (stored) {
          const prefs = JSON.parse(stored);
          const sizeMap: Record<number, string> = { 16: "70ch", 18: "72ch", 20: "76ch", 22: "80ch" };
          root.style.setProperty("--reader-font-size", `${prefs.size / 16}rem`);
          root.style.setProperty("--reader-max-width", sizeMap[prefs.size] ?? "72ch");
        }
      } catch {}
    }
  }, [largeTextMode]);

  useEffect(() => {
    const root = document.documentElement;
    if (compactMode) {
      root.style.setProperty("--reader-paragraph-spacing", "0.75rem");
      root.style.setProperty("--reader-line-height", "1.5");
    } else {
      // Restore from stored reading preferences
      try {
        const stored = localStorage.getItem("tnt_reading_preferences");
        if (stored) {
          const prefs = JSON.parse(stored);
          const spacingMap: Record<string, { line: string; para: string }> = {
            normal:  { line: "1.6", para: "1.25rem" },
            relaxed: { line: "1.8", para: "1.5rem" },
            loose:   { line: "2.0", para: "1.75rem" },
          };
          const s = spacingMap[prefs.spacing] ?? spacingMap.relaxed;
          root.style.setProperty("--reader-line-height", s.line);
          root.style.setProperty("--reader-paragraph-spacing", s.para);
        }
      } catch {}
    }
  }, [compactMode]);

  const createArticleConversation = useCallback(async (articleId: string | number) => {
    try {
      const parsedId = typeof articleId === "number" ? articleId : parseInt(articleId, 10);
      const data = await apiFetch<{ conversation_id: string }>('/chat/conversations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: 'ARTICLE', article_id: isNaN(parsedId) ? null : parsedId }),
      });
      if (data && data.conversation_id) {
        setConversationId(data.conversation_id);
      }
    } catch (err) {
      // Ignore
    }
  }, []);

  useEffect(() => {
    if (rawData?.article?.id && !conversationId) {
      createArticleConversation(rawData.article.id);
    }
  }, [rawData?.article?.id, conversationId, createArticleConversation]);

  // Unpack API response fields
  const { article, content, clean_html, images, knowledge, related, navigation, scoring_debug } = rawData;

  // Reset scroll position to top (0, 0) immediately upon article page mount and after layout paint
  useEffect(() => {
    if (typeof window === "undefined") return;

    // Reset scroll instantly
    window.scrollTo(0, 0);

    // Reinforce reset after next animation frame and 50ms delay (post layout paint)
    const handle = requestAnimationFrame(() => {
      window.scrollTo(0, 0);
    });
    const timer = setTimeout(() => {
      window.scrollTo(0, 0);
    }, 50);

    return () => {
      cancelAnimationFrame(handle);
      clearTimeout(timer);
    };
  }, [article?.id]);

  // ESC to go back (article close gesture)
  // Swipe from left edge handled via CSS touch-action + pointer events
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable
      ) {
        return;
      }

      if (e.key === "Escape") {
        // ESC: if not in focus mode, go back
        if (!focusMode) {
          router.back();
          return;
        }
        setFocusMode(false);
      } else if (e.key === "j" || e.key === "J") {
        if (navigation?.previous?.url) {
          router.push(`/articles/${navigation.previous.url}`);
        }
      } else if (e.key === "k" || e.key === "K") {
        if (navigation?.next?.url) {
          router.push(`/articles/${navigation.next.url}`);
        }
      } else if (e.key === "/") {
        e.preventDefault();
        const searchInput = document.querySelector('input[type="search"]') || document.querySelector('input');
        if (searchInput) (searchInput as HTMLInputElement).focus();
      } else if (e.key === "f" || e.key === "F") {
        e.preventDefault();
        const val = !focusMode;
        setFocusMode(val);
        savePreferences(val, compactMode, largeTextMode);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [navigation, focusMode, compactMode, largeTextMode, router]);


  if (!rawData || !rawData.article) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <h1 className="text-2xl font-mono text-muted-foreground">Article not found</h1>
      </div>
    );
  }

  // Hero Image Fallback Chain: hero_image -> thumbnail_local -> thumbnail_url -> default image
  const heroImageObj = images?.[0] || {};
  const heroImageSrc =
    rawData.hero_image ||
    article.thumbnail_url ||
    article.thumbnail_local ||
    "/images/fallback-article.jpg";

  const heroImageAlt = heroImageObj.alt || article.title;
  const heroImageCaption = heroImageObj.caption || "";
  const heroImageCredit = heroImageObj.credit || "";

  // Hero Image — clip-path vertical wipe + opacity (no blur — GPU expensive on large images)
  // Starts BEFORE the headline in the reveal order (hero occupies half the viewport)

  // Parallax: inner image moves 25px on scroll (barely perceptible — the best kind)

  const heroImageNode = heroImageSrc ? (
    <ArticleRevealSection delay={REVEAL_DELAYS.hero}>
      <figure className="my-8 overflow-hidden rounded-xl border border-border/50 bg-muted/20 relative">
        <div ref={heroRef} className="overflow-hidden" style={{ maxHeight: 450 }}>
          <m.div
            style={!shouldReduceMotion ? { y: heroParallax } : {}}
          >
            <ProgressiveImage
              src={heroImageSrc}
              alt={heroImageAlt}
              className="w-full"
              imgClassName="max-h-[450px] w-full object-cover cursor-zoom-in"
              onClick={() => setLightboxOpen(true)}
            />
          </m.div>
        </div>

        {(heroImageCaption || heroImageCredit) && (
          <figcaption className="p-3 text-center text-xs text-muted-foreground bg-card/60 border-t border-border/30">
            {heroImageCaption}{" "}
            {heroImageCredit && <span className="opacity-60">({heroImageCredit})</span>}
          </figcaption>
        )}

        {article.thumbnail_type === "AI_GENERATED" && (
          <div className="absolute top-4 right-4 bg-primary/90 text-primary-foreground text-xs font-bold px-3 py-1.5 rounded-full flex items-center gap-1.5 shadow-lg backdrop-blur-md">
            <Sparkles className="w-3.5 h-3.5" />
            AI Illustration
          </div>
        )}
      </figure>

      {/* Lightbox */}
      <ImageLightbox
        src={heroImageSrc}
        alt={heroImageAlt}
        isOpen={lightboxOpen}
        onClose={() => setLightboxOpen(false)}
      />
    </ArticleRevealSection>
  ) : null;


  // Key Takeaways Block
  const keyTakeawaysNode = article.key_takeaways && article.key_takeaways.length > 0 ? (
    <div className="bg-card border border-border rounded-xl my-10 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-6 py-4 border-b border-border">
        <span className="text-primary" aria-hidden>⚡</span>
        <h3 className="font-mono text-xs uppercase tracking-wider text-foreground font-bold">
          Key Takeaways
        </h3>
      </div>
      {/* Rows */}
      <div className="divide-y divide-border">
        {article.key_takeaways
          .sort((a: any, b: any) => (a.priority || 3) - (b.priority || 3))
          .map((takeaway: any, idx: number) => (
            <div key={idx} className="flex gap-4 px-6 py-4 items-start">
              <span
                className="flex items-center justify-center w-7 h-7 rounded-full bg-primary/10 text-primary text-xs font-mono font-bold shrink-0 mt-0.5 border border-primary/20"
                aria-label={`Takeaway ${takeaway.priority || idx + 1}`}
              >
                {takeaway.priority || idx + 1}
              </span>
              <div className="space-y-1 min-w-0">
                <h4 className="font-semibold text-sm text-foreground leading-snug">
                  {takeaway.title}
                </h4>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {takeaway.description}
                </p>
              </div>
            </div>
          ))}
      </div>
    </div>
  ) : null;

  // Timeline (only displayed when length >= 2)
  const timelineNode = knowledge?.timeline && knowledge.timeline.length >= 2 ? (
    <div className="bg-card/50 border border-border rounded-xl p-5 my-8">
      <h3 className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-4 flex items-center gap-2">
        <Calendar className="w-4 h-4 text-primary" />
        <span>Timeline of Events</span>
      </h3>
      <div className="relative border-l border-border ml-2 pl-4 py-1 space-y-4">
        {knowledge.timeline.map((event: any, i: number) => (
          <div key={i} className="relative">
            <div className="absolute -left-[21px] top-1.5 w-2.5 h-2.5 bg-primary rounded-full" />
            <div className="text-xs text-muted-foreground font-mono mb-1">{event.date}</div>
            <div className="text-sm text-foreground">{event.description}</div>
          </div>
        ))}
      </div>
    </div>
  ) : null;

  // Explainability Diagnostics Panel
  const explainabilityPanel = scoring_debug ? (
    <div className="bg-card border border-border/60 rounded-xl p-5 my-8 font-mono text-xs text-muted-foreground">
      <h4 className="text-foreground font-bold mb-3 flex items-center gap-2">
        <span>⚙️ Diagnostic: Why this story?</span>
      </h4>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <div className="flex justify-between">
            <span>Base Impact Score:</span>
            <span className="text-foreground">{scoring_debug.base_impact_score}</span>
          </div>
          <div className="flex justify-between">
            <span>Freshness Multiplier:</span>
            <span className="text-foreground">{scoring_debug.freshness_multiplier}</span>
          </div>
          <div className="flex justify-between">
            <span>Effective Score:</span>
            <span className="text-primary font-bold">{scoring_debug.effective_score}</span>
          </div>
        </div>
        <div className="space-y-1.5 border-t md:border-t-0 md:border-l border-border/40 pt-3 md:pt-0 md:pl-4">
          <div className="flex justify-between">
            <span>Decay Model:</span>
            <span className="text-foreground">{scoring_debug.decay_model}</span>
          </div>
          <div className="flex justify-between">
            <span>Time Window:</span>
            <span className="text-foreground">{scoring_debug.window_hours}h</span>
          </div>
          <div className="flex justify-between">
            <span>Algorithm Version:</span>
            <span className="text-foreground">{scoring_debug.algorithm_version}</span>
          </div>
        </div>
      </div>
    </div>
  ) : null;

  // Prev / Next Navigation Footer Card
  const footerNavigationNode = navigation ? (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 border-t border-border/50 pt-8 mt-12">
      {navigation.previous ? (
        <Link href={`/articles/${navigation.previous.url}`} className="group block">
          <div className="bg-card/60 border border-border/40 p-4 rounded-xl hover:bg-card hover:border-border transition-all text-left">
            <span className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground block mb-1">
              ← Previous Story
            </span>
            <h4 className="font-bold text-sm text-foreground group-hover:text-primary line-clamp-1">
              {navigation.previous.title}
            </h4>
          </div>
        </Link>
      ) : (
        <div className="bg-card/30 border border-border/30 p-4 rounded-xl text-muted-foreground opacity-50 flex items-center justify-center text-xs">
          Beginning of feed
        </div>
      )}

      {navigation.next ? (
        <Link href={`/articles/${navigation.next.url}`} className="group block">
          <div className="bg-card/60 border border-border/40 p-4 rounded-xl hover:bg-card hover:border-border transition-all text-right">
            <span className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground block mb-1">
              Next Story →
            </span>
            <h4 className="font-bold text-sm text-foreground group-hover:text-primary line-clamp-1">
              {navigation.next.title}
            </h4>
          </div>
        </Link>
      ) : (
        <div className="bg-card/30 border border-border/30 p-4 rounded-xl text-muted-foreground opacity-50 flex items-center justify-center text-xs">
          End of feed
        </div>
      )}
    </div>
  ) : null;

  const normalizedArticle = normalizeCanonicalArticle(article);
  const normalizedRelated = (related?.articles || []).map((a: any) => normalizeCanonicalArticle(a));

  const relatedContent = (
    <div className="mt-12 space-y-12">
      <ExploreRelatedTopics currentArticle={normalizedArticle} allArticles={normalizedRelated} />

      <div className="pt-8 border-t border-border/40 space-y-6">
        <div className="space-y-1">
          <div className="text-xs font-mono uppercase tracking-widest text-muted-foreground/70 font-semibold">
            Coverage
          </div>
          <h3 className="text-2xl font-bold font-serif text-foreground">Related Stories</h3>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          {normalizedRelated.map((a: CanonicalArticle) => (
            <AdaptiveStoryCard key={a.id} article={a} />
          ))}
        </div>
      </div>
    </div>
  );


  return (
    <>
      <StickyReadingHeader
        title={article.title}
        documentType={article.document_type}
        isMultiTopic={article.is_multi_topic}
        readingTimeMin={article.reading_time || 5}
        largeTextMode={largeTextMode}
        onToggleLargeText={() => {
          const val = !largeTextMode;
          setLargeTextMode(val);
          savePreferences(focusMode, compactMode, val);
        }}
      />
      <ReadingProgress wordCount={article.word_count || content?.split(/\s+/).length || 500} />

      <ArticleLayout
        focusMode={focusMode}
        actions={
          <FloatingActions
            url={typeof window !== "undefined" ? window.location.href : ""}
            title={article.title}
            articleId={article.id}
          />
        }
        header={
          <div className="space-y-6">
            <ArticleHeader
              title={article.title}
              category={article.category || "News"}
              publishedAt={article.published_at ? new Date(article.published_at).toISOString() : new Date().toISOString()}
              readingTimeMin={article.reading_time || 5}
              documentType={article.document_type}
              isMultiTopic={article.is_multi_topic}
            />
            {/* Reading Preferences Control Bar — compacts when scrolled (reading focus) */}
            <div
              className={cn(
                "flex items-center justify-between border-t border-b border-border/50 transition-all duration-300 ease-out",
                isReadingMode ? "py-1.5" : "py-3"
              )}
            >
              <div className="flex items-center gap-2 sm:gap-3 flex-wrap text-xs font-mono">
                <span className="text-muted-foreground uppercase tracking-wider hidden sm:inline font-semibold">Mode:</span>
                <button
                  type="button"
                  onClick={() => {
                    const val = !focusMode;
                    setFocusMode(val);
                    savePreferences(val, compactMode, largeTextMode);
                  }}
                  className={cn(
                    "motion-btn inline-flex items-center gap-1.5 px-3 py-1 rounded-full border transition-all text-[11px] font-semibold",
                    focusMode
                      ? "bg-primary text-primary-foreground border-primary shadow-sm"
                      : "border-border/60 text-muted-foreground hover:text-foreground hover:bg-muted/30"
                  )}
                >
                  <Eye className="w-3 h-3" strokeWidth={1.75} />
                  <span>Zen Focus</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    const val = !compactMode;
                    setCompactMode(val);
                    savePreferences(focusMode, val, largeTextMode);
                  }}
                  className={cn(
                    "motion-btn inline-flex items-center gap-1.5 px-3 py-1 rounded-full border transition-all text-[11px] font-semibold",
                    compactMode
                      ? "bg-primary text-primary-foreground border-primary shadow-sm"
                      : "border-border/60 text-muted-foreground hover:text-foreground hover:bg-muted/30"
                  )}
                >
                  <Minimize2 className="w-3 h-3" strokeWidth={1.75} />
                  <span>Compact</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    const val = !largeTextMode;
                    setLargeTextMode(val);
                    savePreferences(focusMode, compactMode, val);
                  }}
                  className={cn(
                    "motion-btn inline-flex items-center gap-1.5 px-3 py-1 rounded-full border transition-all text-[11px] font-semibold",
                    largeTextMode
                      ? "bg-primary text-primary-foreground border-primary shadow-sm"
                      : "border-border/60 text-muted-foreground hover:text-foreground hover:bg-muted/30"
                  )}
                >
                  <Type className="w-3 h-3" strokeWidth={1.75} />
                  <span>Large Text</span>
                </button>
              </div>
              <ReadingPreferences />
            </div>
          </div>
        }
        heroImageNode={heroImageNode}
        // AI Summary reveals first after hero — reinforces product identity
        aiSummary={
          <ArticleRevealSection delay={REVEAL_DELAYS.meta + 0.08}>
            <AISummaryCard
              summary={article.summary || ""}
            />
          </ArticleRevealSection>
        }
        sourceCredibility={
          <SourceCredibility
            sourceName={article.source}
            sourceUrl={article.url}
            credibilityScore={"85"}
            aiConfidence={"95"}
            publishedAt={article.published_at ? new Date(article.published_at).toISOString() : new Date().toISOString()}
          />
        }
        toc={
          <TableOfContents selector="div.prose-theme" />
        }
        content={
          <ArticleRevealSection delay={REVEAL_DELAYS.body}>
            <ArticleReader content={clean_html || content || ""} />
          </ArticleRevealSection>
        }
        keyTakeaways={keyTakeawaysNode}
        askAI={
          <div className="space-y-6">
            <ConversationalSearch
              conversationId={conversationId}
              articleId={article.id}
              articleTitle={article.title}
              keywords={[]}
              initialMode="ARTICLE"
              hideModeSelector={true}
              showOpenFullChat={true}
            />
            {explainabilityPanel}
          </div>
        }
        timeline={timelineNode}
        knowledgePanel={
          <KnowledgePanel
            entities={knowledge?.entities}
            topics={knowledge?.topics}
            timeline={knowledge?.timeline}
            relationships={knowledge?.relationships}
          />
        }
        related={relatedContent}
        navigation={footerNavigationNode}
      />
    </>
  );
}
