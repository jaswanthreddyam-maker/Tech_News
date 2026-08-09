/**
 * ArticleLink Domain Behavior Specification & Documented Testing Contract
 * 
 * 1. Internal Route: Renders Next.js <Link href="/articles/[slug]"> for clean string slugs.
 * 2. External Route: Renders <a> with target="_blank" and rel="noopener noreferrer" for http(s) URLs.
 * 3. Invalid Route: Renders disabled container with aria-disabled="true" and title="Article unavailable".
 * 4. 150ms Debounced Hover Prefetch: Intent delay timer (150ms) prevents cursor sweep floods.
 */
export const ARTICLE_LINK_SPEC = {
  PREFETCH_INTENT_DELAY_MS: 150,
  TARGET_EXTERNAL: "_blank",
  REL_EXTERNAL: "noopener noreferrer",
};
