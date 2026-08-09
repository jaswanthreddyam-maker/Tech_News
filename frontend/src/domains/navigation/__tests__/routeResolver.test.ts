import { resolveArticleRoute } from "../routeResolver";

/**
 * Navigation Domain Unit Test Assertions
 */
export function runRouteResolverTests(): { passed: number; total: number } {
  let passed = 0;
  let total = 0;

  function assert(condition: boolean, message: string) {
    total++;
    if (!condition) {
      throw new Error(`Test Failed: ${message}`);
    }
    passed++;
  }

  // Test 1: Clean internal slug
  const r1 = resolveArticleRoute({ id: 1, slug: "ai-breakthrough-2026", title: "AI Breakthrough" });
  assert(r1.kind === "internal" && r1.href === "/articles/ai-breakthrough-2026", "Internal slug resolution");

  // Test 2: Clean external publisher URL
  const r2 = resolveArticleRoute({ id: 2, slug: null, url: "https://theverge.com/tech/ai-article", title: "Verge" });
  assert(r2.kind === "external" && r2.href === "https://theverge.com/tech/ai-article", "External URL resolution");

  // Test 3: Prioritizes valid slug over external URL
  const r3 = resolveArticleRoute({ id: 3, slug: "internal-slug", url: "https://external.com", title: "Dual" });
  assert(r3.kind === "internal" && r3.href === "/articles/internal-slug", "Slug priority");

  // Test 4: Blocks dangerous javascript: scheme
  const r4 = resolveArticleRoute({ id: 4, slug: null, url: "javascript:alert(1)", title: "Dangerous" });
  assert(r4.kind === "invalid", "Block javascript: scheme");

  // Test 5: Blocks dangerous data: scheme
  const r5 = resolveArticleRoute({ id: 5, slug: null, url: "data:text/html,<script>", title: "Data Scheme" });
  assert(r5.kind === "invalid", "Block data: scheme");

  // Test 6: Blocks ftp: scheme
  const r6 = resolveArticleRoute({ id: 6, slug: null, url: "ftp://server.com/file", title: "FTP Scheme" });
  assert(r6.kind === "invalid", "Block ftp: scheme");

  // Test 7: ID fallback resolution when slug is null
  const r7 = resolveArticleRoute({ id: 7, slug: null, url: null, title: "ID Fallback" });
  assert(r7.kind === "internal" && r7.href === "/articles/7", "ID fallback resolution");

  // Test 8: Missing id, slug, and URL is invalid
  const r8 = resolveArticleRoute({ id: undefined as any, slug: null, url: null, title: "Empty" });
  assert(r8.kind === "invalid", "Missing id, slug and URL");

  // Test 9: Null article is invalid
  const r9 = resolveArticleRoute(null);
  assert(r9.kind === "invalid", "Null article");

  return { passed, total };
}
