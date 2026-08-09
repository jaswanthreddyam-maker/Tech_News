# Thumbnail Pipeline — Runtime Verification & Provenance Report

> **Audit Context**: Verification of thumbnail pipeline claims through empirical database queries, code inspection, and runtime trace analysis.

---

## 1. Thumbnail Provenance Table (10 Sample Articles)

The table below traces 10 real articles from database storage to read model projection and frontend resolution:

| ID | Title | Ingestion Status | Winner Pass | Thumbnail Source | Processed DB Local | Read Model Local | Frontend Chosen Target |
|---|---|---|---|---|---|---|---|
| **37** | NVIDIA Harnesses Vera CPU to Speed Up... | `downloaded` | `strict` | `og:image` | `/api/v1/uploads/thumbnails/cccc3...` | `/api/v1/uploads/thumbnails/cccc3...` | 🔴 `https://blogs.nvidia.com/...` (Remote URL) |
| **38** | At AI Summit, South Korea Outlines... | `downloaded` | `strict` | `og:image` | `/api/v1/uploads/thumbnails/c1c09...` | `/api/v1/uploads/thumbnails/c1c09...` | 🔴 `https://blogs.nvidia.com/...` (Remote URL) |
| **39** | GFN Thursday: New 'Path of Exile'... | `downloaded` | `strict` | `og:image` | `/api/v1/uploads/thumbnails/c0300...` | `/api/v1/uploads/thumbnails/c0300...` | 🔴 `https://blogs.nvidia.com/...` (Remote URL) |
| **40** | AI Supercomputer Comes Online at... | `downloaded` | `strict` | `og:image` | `/api/v1/uploads/thumbnails/ee5fd...` | `/api/v1/uploads/thumbnails/ee5fd...` | 🔴 `https://blogs.nvidia.com/...` (Remote URL) |
| **41** | NVIDIA Open Sources First GPU... | `downloaded` | `strict` | `og:image` | `/api/v1/uploads/thumbnails/e43f0...` | `/api/v1/uploads/thumbnails/e43f0...` | 🔴 `https://blogs.nvidia.com/...` (Remote URL) |
| **111** | Satya Nadella says companies... | `pending` | `N/A` | `N/A` | `None` | `None` | ⚪ Fallback SVG |
| **113** | Microsoft launches its first cyber... | `pending` | `N/A` | `N/A` | `None` | `None` | ⚪ Fallback SVG |
| **115** | OpenAI's biggest threat may just... | `pending` | `N/A` | `N/A` | `None` | `None` | ⚪ Fallback SVG |
| **36** | Industry Leaders Join Open Secure... | `failed` | `fallback` | `fallback` | `None` | `None` | ⚪ Fallback SVG |
| **60** | Mix local LLMs, Claude Code... | `failed` | `fallback` | `fallback` | `None` | `None` | ⚪ Fallback SVG |

---

## 2. Verification of Key Claims

### Claim 1: "Remote URL Preferred Over Local"
- **Verification Result**: **CONFIRMED ARCHITECTURAL DEFECT**
- **Evidence**:
  1. For downloaded articles (e.g. ID 37-41), `thumbnail_local` is **fully populated** in both `ProcessedArticle` and `ArticleReadModel` with `/api/v1/uploads/thumbnails/{hash}.webp`. `thumbnail_local` is **NOT null**.
  2. In `thumbnailService.ts` ([L27-37](file:///d:/tech_news/frontend/src/lib/thumbnails/thumbnailService.ts#L27-L37)):
     ```typescript
     if (article.thumbnail_url) return article.thumbnail_url; // Remote URL returned FIRST
     if (article.thumbnail_local) return article.thumbnail_local;
     ```
  3. Because `thumbnail_url` is non-null, `getPublicImageUrl` returns the external remote HTTP URL (`https://blogs.nvidia.com/...`) and **never reaches** line 31 (`thumbnail_local`).
  4. The browser is forced to fetch the image from third-party remote CDNs, completely bypassing the local optimized WebP asset.

---

### Claim 2: "28 / 56 Pending Thumbnails"
- **Verification Result**: **CONFIRMED (Exact SQL Breakdown)**
- **SQL Execution**:
  ```sql
  SELECT thumbnail_status, COUNT(*) 
  FROM processed_articles 
  GROUP BY thumbnail_status;
  ```
- **Output**:
  - `downloaded`: **23**
  - `pending`: **28**
  - `failed`: **5**
  - Total: **56**
- **Read Model Status Alignment**:
  ```sql
  SELECT (thumbnail_url IS NOT NULL AND thumbnail_local IS NOT NULL) AS has_thumbnail, COUNT(*)
  FROM articles
  GROUP BY (thumbnail_url IS NOT NULL AND thumbnail_local IS NOT NULL);
  ```
  - `has_thumbnail = True`: **23**
  - `has_thumbnail = False`: **33** (28 pending + 5 failed/null)

---

### Claim 3: SSRF Re-Classification
- **Original Audit Rating**: CRITICAL
- **Re-Classified Rating**: **HIGH**
- **Rationale**: Ingestion sources are configured via the PostgreSQL `SourceRegistry` (trusted RSS feeds from established tech sites like TechCrunch, The Verge, NVIDIA, DeepMind). However, if an ingested feed contains a poisoned `og:image` link pointing to internal subnets (`169.254.169.254` or `127.0.0.1`), `httpx.AsyncClient` in `download_and_validate_in_memory` will attempt to fetch it because no IP range whitelist/blacklist filter is enforced.

---

### Claim 4: pHash Collisions & Shared Assets
- **Finding**: When two different articles yield identical visual pHashes (e.g. identical generic publisher banner or placeholder graphics), `save_image_to_disk` reuses `/app/uploads/thumbnails/{phash}.webp`.
- **Impact**: Both articles point to the same WebP file on disk. This is storage-efficient, but requires that single asset files are never deleted when an individual article is deleted or updated.

---

### Claim 5: Operational Recovery for Pending Items
- **Finding**:
  - **Automated Cron**: **No background recovery worker** exists to automatically retry `thumbnail_status = 'pending'` articles after a Redis or network outage.
  - **Manual / Admin Tools**:
    - CLI repair scripts exist: `fix_thumbnails.py`, `rebuild_content.py`.
    - Admin API endpoint exists: `POST /api/v1/admin/sources/{id}/trigger` (force crawl single source).

---

### Claim 6: CDN, Browser Headers & Caching Audit
- **FastAPI Uploads Endpoint**: `app.mount("/api/v1/uploads", StaticFiles(directory="/app/uploads"))` in [main.py L171](file:///d:/tech_news/backend/main.py#L171) relies on default Starlette static headers (no custom long-term `Cache-Control: public, max-age=31536000` or `ETag` overrides).
- **Redis Cache**: `editorial:v1:homepage_ranked_ids` holds article ID rankings for 1 hour (`ex=3600`). If a thumbnail task finishes while an article is cached, the cached article payload in Redis will not reflect the new thumbnail until TTL expires.
- **Frontend Blur Data**: `thumbnailService.ts` provides a generic 1x1 base64 gray blur placeholder (`GENERIC_BLUR`), bypassing expensive per-image blurhash computation.

---

### Claim 7: Projection Freshness & Data Model Alignment
- **ProcessedArticle vs. ArticleReadModel**:
  - For downloaded articles (IDs 37-41), `ProcessedArticle.thumbnail_local` and `ArticleReadModel.thumbnail_local` are **100% in sync** (`/api/v1/uploads/thumbnails/{hash}.webp`).
  - **Column Overload**: `ArticleReadModel.hash` contains the raw article ID for pending items (`77`, `75`), but gets overwritten with the 64-bit thumbnail pHash (`cccc333333333333`) when `ArticleThumbnailUpdated` event is processed.
