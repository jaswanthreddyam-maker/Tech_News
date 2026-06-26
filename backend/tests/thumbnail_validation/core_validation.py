"""
Thumbnail Certification Framework — Core Validation Engine.

Contains:
- PipelineStageTracker: measures latency for each pipeline stage.
- validate_article_thumbnail(): runs the full extraction pipeline on a single article.
- calculate_grades(): assigns a letter grade based on fallback rate.
- generate_report(): produces Markdown + JSON reports with domain leaderboard,
  winner distribution, failure samples, version metadata, and historical comparison.
"""

import datetime
import json
import os
import platform
import subprocess
import sys
import time
import zlib
from typing import Any
from urllib.parse import urlparse

# Add backend root to path so image_helper can be imported standalone
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.services.ingestion.image_helper import (
    download_and_validate_in_memory,
    extract_all_candidate_urls,
)

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")
HISTORY_DIR = os.path.join(REPORTS_DIR, "history")

# ─── Quality Gate Thresholds ───────────────────────────────────────────────
QUALITY_GATES = {
    "max_fallback_rate": 3.0,  # %
    "min_avg_candidates": 3,
    "max_duplicate_rate": 2.0,  # %
    "min_avg_html_bytes": 40_000,
    "max_download_failure_rate": 2.0,  # %
    "max_avg_processing_sec": 2.0,
}

# All recognized failure reasons for categorization
FAILURE_CATEGORIES = [
    "0 candidates",
    "html_too_short",
    "network_timeout",
    "http_403",
    "http_404",
    "ssl_failure",
    "connection_error",
    "download_failure",
    "dimension_filter",
    "aspect_ratio_filter",
    "keyword_penalty",
    "invalid_content_type",
    "logo_detected",
    "duplicate_image",
]


# ─── Pipeline Stage Tracker ───────────────────────────────────────────────
class PipelineStageTracker:
    """Measures wall-clock latency for every named pipeline stage."""

    def __init__(self):
        self.timings: dict[str, float] = {}
        self._starts: dict[str, float] = {}

    def start(self, stage: str):
        self._starts[stage] = time.perf_counter()

    def end(self, stage: str):
        t0 = self._starts.pop(stage, None)
        if t0 is not None:
            self.timings[stage] = round(time.perf_counter() - t0, 4)

    async def ameasure(self, stage: str, coro):
        """Await *coro* and record the time under *stage*."""
        self.start(stage)
        result = await coro
        self.end(stage)
        return result


# ─── Single Article Validation ─────────────────────────────────────────────
async def validate_article_thumbnail(
    html_content: str,
    article_url: str,
) -> dict[str, Any]:
    """
    Run the full thumbnail extraction pipeline on one article and return
    a result dict containing metrics for every stage.
    """
    tracker = PipelineStageTracker()
    total_start = time.perf_counter()

    # Stage 1 — HTML Preservation
    tracker.start("html_preservation")
    raw_bytes = html_content.encode("utf-8", errors="replace") if html_content else b""
    raw_len = len(raw_bytes)
    compressed = zlib.compress(raw_bytes, 6) if raw_bytes else b""
    clean_len = raw_len  # same content; we measure ratio vs zlib
    compression_ratio = round(raw_len / len(compressed), 2) if compressed else 0
    tracker.end("html_preservation")

    # Stage 2 — Candidate Discovery
    tracker.start("candidate_discovery")
    candidates = extract_all_candidate_urls(html_content, article_url) if html_content else []
    tracker.end("candidate_discovery")

    # Stage 3 — Candidate Scoring (already sorted by extract_all_candidate_urls)
    tracker.start("candidate_scoring")
    # scoring happens inside extract_all_candidate_urls, so this is a no-op
    # but we keep the stage for latency tracking
    tracker.end("candidate_scoring")

    # Stage 4 — Image Download + Validation + Winner Selection
    tracker.start("image_download_validation")
    winner_source = "fallback"
    winner_url = None
    winner_dims = None
    winner_phash = None
    failure_reason = "0 candidates" if not candidates else None
    rejection_log: list[dict[str, Any]] = []

    for c in candidates:
        img, phash, rej_reason, dims = await download_and_validate_in_memory(c["url"], relaxed=True)
        if rej_reason is None:
            # winner found
            winner_url = c["url"]
            winner_source = c.get("source", "unknown")
            winner_dims = dims
            winner_phash = phash
            failure_reason = None
            break
        else:
            rejection_log.append(
                {
                    "url": c["url"],
                    "source": c.get("source", "unknown"),
                    "reason": rej_reason,
                    "dims": dims,
                }
            )
            failure_reason = rej_reason  # last failure becomes the reported one

    tracker.end("image_download_validation")

    total_elapsed = round(time.perf_counter() - total_start, 4)

    return {
        "url": article_url,
        "domain": urlparse(article_url).netloc.replace("www.", ""),
        "raw_html_length": raw_len,
        "clean_html_length": clean_len,
        "compression_ratio": compression_ratio,
        "candidate_count": len(candidates),
        "winner_source": winner_source,
        "winner_url": winner_url,
        "winner_phash": winner_phash,
        "winner_dims": winner_dims,
        "is_fallback": winner_source == "fallback",
        "failure_reason": failure_reason,
        "rejection_log": rejection_log,
        "timings": tracker.timings,
        "total_time_sec": total_elapsed,
    }


# ─── Grading ───────────────────────────────────────────────────────────────
def calculate_grade(fallback_rate: float) -> str:
    if fallback_rate < 1.0:
        return "A+"
    if fallback_rate < 2.0:
        return "A"
    if fallback_rate < 5.0:
        return "B"
    if fallback_rate < 10.0:
        return "C"
    return "FAIL"


# ─── Version Metadata ─────────────────────────────────────────────────────
def _get_version_metadata() -> dict[str, str]:
    git_commit = "unknown"
    try:
        git_commit = (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=BACKEND_ROOT,
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except Exception:
        pass

    return {
        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "python_version": platform.python_version(),
        "os": f"{platform.system()} {platform.release()}",
        "git_commit": git_commit,
    }


# ─── Historical Comparison ────────────────────────────────────────────────
def _load_previous_run(run_type: str) -> dict | None:
    """Load the most recent historical JSON for *run_type*."""
    history_file = os.path.join(HISTORY_DIR, f"latest_{run_type}.json")
    if os.path.exists(history_file):
        with open(history_file, encoding="utf-8") as f:
            return json.load(f)
    return None


def _trend(current: float, previous: float, lower_is_better: bool = True) -> str:
    """Return a trend arrow with label."""
    if previous is None or previous == 0:
        return "—"
    diff = current - previous
    if abs(diff) < 0.01:
        return "→ No change"
    if lower_is_better:
        return (
            f"↓ {previous:.1f} → {current:.1f} ✅ Improved"
            if diff < 0
            else f"↑ {previous:.1f} → {current:.1f} ⚠️ Regressed"
        )
    else:
        return (
            f"↑ {previous:.1f} → {current:.1f} ✅ Improved"
            if diff > 0
            else f"↓ {previous:.1f} → {current:.1f} ⚠️ Regressed"
        )


# ─── Report Generation ────────────────────────────────────────────────────
def generate_report(results: list[dict], run_type: str) -> dict[str, Any]:
    """
    Generate Markdown + JSON reports from a list of article validation results.
    Returns the summary dict (also saved as JSON).
    """
    os.makedirs(os.path.join(REPORTS_DIR, "markdown"), exist_ok=True)
    os.makedirs(os.path.join(REPORTS_DIR, "json"), exist_ok=True)
    os.makedirs(HISTORY_DIR, exist_ok=True)

    total = len(results)
    if total == 0:
        print("No results to report.")
        return {}

    # ── Aggregate metrics ────────────────────────────────────────────
    fallbacks = sum(1 for r in results if r["is_fallback"])
    fallback_rate = (fallbacks / total) * 100
    avg_html = sum(r["raw_html_length"] for r in results) / total
    avg_candidates = sum(r["candidate_count"] for r in results) / total
    avg_time = sum(r["total_time_sec"] for r in results) / total

    # Duplicate detection via pHash
    phash_seen: dict[str, str] = {}
    duplicate_count = 0
    for r in results:
        ph = r.get("winner_phash")
        if ph:
            if ph in phash_seen:
                duplicate_count += 1
            else:
                phash_seen[ph] = r["url"]
    duplicate_rate = (duplicate_count / total) * 100

    # Download failures
    download_failures = sum(
        1
        for r in results
        if r.get("failure_reason")
        in (
            "download_failure",
            "network_timeout",
            "connection_error",
            "ssl_failure",
            "http_403",
            "http_404",
        )
    )
    download_failure_rate = (download_failures / total) * 100

    # ── Per-domain statistics ────────────────────────────────────────
    domains: dict[str, dict] = {}
    for r in results:
        d = r["domain"]
        if d not in domains:
            domains[d] = {
                "total": 0,
                "fallbacks": 0,
                "candidates": 0,
                "html_bytes": 0,
                "duplicates": 0,
                "total_time": 0.0,
            }
        ds = domains[d]
        ds["total"] += 1
        ds["candidates"] += r["candidate_count"]
        ds["html_bytes"] += r["raw_html_length"]
        ds["total_time"] += r["total_time_sec"]
        if r["is_fallback"]:
            ds["fallbacks"] += 1

    # ── Winner distribution ──────────────────────────────────────────
    winner_dist: dict[str, int] = {}
    for r in results:
        src = r["winner_source"]
        winner_dist[src] = winner_dist.get(src, 0) + 1

    # ── Failure reason breakdown ─────────────────────────────────────
    failure_reasons: dict[str, int] = {}
    for r in results:
        if r["is_fallback"] and r.get("failure_reason"):
            reason = r["failure_reason"]
            failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

    # ── Quality gate evaluation ──────────────────────────────────────
    gates_passed = {
        "fallback_rate": fallback_rate < QUALITY_GATES["max_fallback_rate"],
        "avg_candidates": avg_candidates > QUALITY_GATES["min_avg_candidates"],
        "duplicate_rate": duplicate_rate < QUALITY_GATES["max_duplicate_rate"],
        "avg_html_bytes": avg_html > QUALITY_GATES["min_avg_html_bytes"],
        "download_failure_rate": download_failure_rate < QUALITY_GATES["max_download_failure_rate"],
        "avg_processing_time": avg_time < QUALITY_GATES["max_avg_processing_sec"],
    }
    all_passed = all(gates_passed.values())
    status = "PASS" if all_passed else "FAIL"
    grade = calculate_grade(fallback_rate)

    # ── Version metadata ─────────────────────────────────────────────
    version_meta = _get_version_metadata()

    # ── Historical comparison ────────────────────────────────────────
    prev = _load_previous_run(run_type)
    trends = {}
    if prev:
        trends["fallback_rate"] = _trend(fallback_rate, prev.get("fallback_rate"), lower_is_better=True)
        trends["avg_candidates"] = _trend(avg_candidates, prev.get("avg_candidates"), lower_is_better=False)
        trends["avg_html_kb"] = _trend(avg_html / 1024, prev.get("avg_html_bytes", 0) / 1024, lower_is_better=False)
        trends["duplicate_rate"] = _trend(duplicate_rate, prev.get("duplicate_rate"), lower_is_better=True)
        trends["avg_time"] = _trend(avg_time, prev.get("avg_processing_time"), lower_is_better=True)

    # ══════════════════════════════════════════════════════════════════
    #  Build JSON summary (machine-readable)
    # ══════════════════════════════════════════════════════════════════
    summary = {
        **version_meta,
        "run_type": run_type,
        "grade": grade,
        "status": status,
        "total_articles": total,
        "fallback_count": fallbacks,
        "fallback_rate": round(fallback_rate, 2),
        "duplicate_count": duplicate_count,
        "duplicate_rate": round(duplicate_rate, 2),
        "avg_html_bytes": round(avg_html, 0),
        "avg_candidates": round(avg_candidates, 2),
        "avg_processing_time": round(avg_time, 4),
        "download_failure_rate": round(download_failure_rate, 2),
        "quality_gates": gates_passed,
        "domains": {
            d: {
                "total": s["total"],
                "fallback_pct": round((s["fallbacks"] / s["total"]) * 100, 1),
                "duplicate_pct": round((s["duplicates"] / s["total"]) * 100, 1) if s["total"] else 0,
                "avg_html_kb": round(s["html_bytes"] / s["total"] / 1024, 1),
                "avg_candidates": round(s["candidates"] / s["total"], 1),
                "avg_time_sec": round(s["total_time"] / s["total"], 2),
            }
            for d, s in domains.items()
        },
        "winner_distribution": winner_dist,
        "failure_reasons": failure_reasons,
        "trends": trends,
    }

    json_path = os.path.join(REPORTS_DIR, "json", f"report_{run_type}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Save as latest for next comparison
    history_path = os.path.join(HISTORY_DIR, f"latest_{run_type}.json")
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # ══════════════════════════════════════════════════════════════════
    #  Build Markdown report (human-readable)
    # ══════════════════════════════════════════════════════════════════
    lines = ["# Thumbnail Certification Report", ""]

    # Certification Badge
    lines.append("## Certification Badge")
    lines.append("")
    lines.append("| Grade | Articles | Fallback Rate | Duplicate Rate | Avg Candidates | Avg Time | Status |")
    lines.append("|:---:|:---:|:---:|:---:|:---:|:---:|:---:|")
    lines.append(
        f"| **{grade}** | {total} | {fallback_rate:.1f}% | {duplicate_rate:.1f}% "
        f"| {avg_candidates:.1f} | {avg_time:.2f}s | **{status}** |"
    )
    lines.append("")

    # Version Metadata
    lines.append("## Version Metadata")
    lines.append(f"- **Date**: {version_meta['date']}")
    lines.append(f"- **Git Commit**: `{version_meta['git_commit']}`")
    lines.append(f"- **Python**: {version_meta['python_version']}")
    lines.append(f"- **OS**: {version_meta['os']}")
    lines.append(f"- **Run Type**: {run_type}")
    lines.append("")

    # Historical Trends
    if trends:
        lines.append("## Trend vs Previous Run")
        lines.append("")
        lines.append("| Metric | Trend |")
        lines.append("|---|---|")
        for k, v in trends.items():
            lines.append(f"| {k} | {v} |")
        lines.append("")

    # Quality Gates
    lines.append("## Quality Gates")
    lines.append("")
    lines.append("| Metric | Value | Threshold | Result |")
    lines.append("|---|---|---|---|")
    lines.append(
        f"| Fallback Rate | {fallback_rate:.1f}% | < {QUALITY_GATES['max_fallback_rate']}% | {'✅' if gates_passed['fallback_rate'] else '❌'} |"
    )
    lines.append(
        f"| Avg Candidates | {avg_candidates:.1f} | > {QUALITY_GATES['min_avg_candidates']} | {'✅' if gates_passed['avg_candidates'] else '❌'} |"
    )
    lines.append(
        f"| Duplicate Rate | {duplicate_rate:.1f}% | < {QUALITY_GATES['max_duplicate_rate']}% | {'✅' if gates_passed['duplicate_rate'] else '❌'} |"
    )
    lines.append(
        f"| Avg HTML | {avg_html / 1024:.1f} KB | > {QUALITY_GATES['min_avg_html_bytes'] / 1024:.0f} KB | {'✅' if gates_passed['avg_html_bytes'] else '❌'} |"
    )
    lines.append(
        f"| Download Failures | {download_failure_rate:.1f}% | < {QUALITY_GATES['max_download_failure_rate']}% | {'✅' if gates_passed['download_failure_rate'] else '❌'} |"
    )
    lines.append(
        f"| Avg Processing Time | {avg_time:.2f}s | < {QUALITY_GATES['max_avg_processing_sec']}s | {'✅' if gates_passed['avg_processing_time'] else '❌'} |"
    )
    lines.append("")

    # Domain Leaderboard
    sorted_domains = sorted(
        domains.items(),
        key=lambda x: (x[1]["fallbacks"] / x[1]["total"]) if x[1]["total"] else 999,
    )
    lines.append("## Domain Leaderboard")
    lines.append("")
    lines.append("| # | Domain | Articles | Fallback % | Avg HTML | Avg Cands | Avg Time |")
    lines.append("|:---:|---|:---:|:---:|:---:|:---:|:---:|")
    for rank, (d, s) in enumerate(sorted_domains, 1):
        fb_pct = (s["fallbacks"] / s["total"]) * 100 if s["total"] else 0
        avg_h = s["html_bytes"] / s["total"] / 1024 if s["total"] else 0
        avg_c = s["candidates"] / s["total"] if s["total"] else 0
        avg_t = s["total_time"] / s["total"] if s["total"] else 0
        lines.append(f"| {rank} | {d} | {s['total']} | {fb_pct:.1f}% | {avg_h:.1f}k | {avg_c:.1f} | {avg_t:.2f}s |")
    lines.append("")

    # Winner Distribution
    lines.append("## Winner Distribution")
    lines.append("")
    sorted_winners = sorted(winner_dist.items(), key=lambda x: x[1], reverse=True)
    for src, count in sorted_winners:
        pct = (count / total) * 100
        lines.append(f"- **{src}**: {pct:.1f}% ({count})")
    lines.append("")

    # Failure Reason Breakdown
    if failure_reasons:
        lines.append("## Failure Reasons")
        lines.append("")
        sorted_failures = sorted(failure_reasons.items(), key=lambda x: x[1], reverse=True)
        for reason, count in sorted_failures:
            lines.append(f"- **{reason}**: {count}")
        lines.append("")

    # Failure Samples (up to 10)
    fallback_results = [r for r in results if r["is_fallback"]]
    if fallback_results:
        lines.append("## Failure Samples")
        lines.append("")
        for sample in fallback_results[:10]:
            lines.append(f"### `{sample['url']}`")
            lines.append(f"- **Reason**: {sample.get('failure_reason', 'unknown')}")
            lines.append(f"- **HTML Length**: {sample['raw_html_length']:,} bytes")
            lines.append(f"- **Candidates Found**: {sample['candidate_count']}")
            if sample.get("rejection_log"):
                lines.append("- **Rejections**:")
                for rej in sample["rejection_log"][:5]:
                    lines.append(f"  - `{rej['source']}` → {rej['reason']} ({rej['url'][:80]}…)")
            lines.append("")

    md_content = "\n".join(lines)
    md_path = os.path.join(REPORTS_DIR, "markdown", f"report_{run_type}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"\n{'=' * 60}")
    print(f"  THUMBNAIL CERTIFICATION — {run_type.upper()}")
    print(f"{'=' * 60}")
    print(f"  Grade:          {grade}")
    print(f"  Status:         {status}")
    print(f"  Articles:       {total}")
    print(f"  Fallback Rate:  {fallback_rate:.1f}%")
    print(f"  Duplicate Rate: {duplicate_rate:.1f}%")
    print(f"  Avg Candidates: {avg_candidates:.1f}")
    print(f"  Avg HTML:       {avg_html / 1024:.1f} KB")
    print(f"  Avg Time:       {avg_time:.2f}s")
    print(f"{'=' * 60}")
    print(f"  Markdown: {md_path}")
    print(f"  JSON:     {json_path}")
    print(f"{'=' * 60}\n")

    return summary
