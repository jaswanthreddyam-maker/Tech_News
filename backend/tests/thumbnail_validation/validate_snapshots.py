"""
Thumbnail Certification Framework — Snapshot Validation (Mode B).

Runs the thumbnail extraction pipeline against locally saved HTML fixtures.
No internet required. Deterministic. CI-friendly.

Gold Standard assertions: if an expected/<domain>/<slug>.json file exists,
the script validates that the pipeline output matches expectations.

Usage:
    cd backend
    set PYTHONPATH=.
    venv\\Scripts\\python.exe -m tests.thumbnail_validation.validate_snapshots

Exit code:
    0  — All quality gates passed
    1  — One or more quality gates failed
"""

import asyncio
import json
import os
import sys

# Ensure UTF-8 console output on Windows/etc.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from tests.thumbnail_validation.core_validation import (
    generate_report,
    validate_article_thumbnail,
)

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
HTML_DIR = os.path.join(FIXTURES_DIR, "html")
EXPECTED_DIR = os.path.join(FIXTURES_DIR, "expected")


async def run_snapshots():
    results = []
    gold_standard_failures = []

    if not os.path.exists(HTML_DIR):
        print(f"ERROR: HTML fixtures directory not found: {HTML_DIR}")
        print("Run generate_fixtures.py first to create snapshots.")
        sys.exit(1)

    domain_dirs = [d for d in os.listdir(HTML_DIR) if os.path.isdir(os.path.join(HTML_DIR, d))]

    if not domain_dirs:
        print("ERROR: No domain directories found in fixtures/html/")
        print("Run generate_fixtures.py first.")
        sys.exit(1)

    total_fixtures = 0
    for domain in sorted(domain_dirs):
        domain_dir = os.path.join(HTML_DIR, domain)
        html_files = [f for f in os.listdir(domain_dir) if f.endswith(".html")]
        total_fixtures += len(html_files)

        for html_file in sorted(html_files):
            slug = html_file[:-5]  # strip .html
            html_path = os.path.join(domain_dir, html_file)
            expected_path = os.path.join(EXPECTED_DIR, domain, f"{slug}.json")

            # Read HTML fixture
            with open(html_path, encoding="utf-8", errors="replace") as f:
                html_content = f.read()

            # Read expected JSON (Gold Standard)
            expected = {}
            expected_url = f"https://{domain}/{slug.replace('_', '/')}"
            if os.path.exists(expected_path):
                with open(expected_path, encoding="utf-8") as f:
                    expected = json.load(f)
                expected_url = expected.get("expected_url", expected_url)

            # Run pipeline
            result = await validate_article_thumbnail(html_content, expected_url)

            # Gold Standard Assertions
            if expected:
                gs_fail = []
                if expected.get("expected_fallback") is False and result["is_fallback"]:
                    gs_fail.append(f"Expected a thumbnail but got fallback (reason: {result.get('failure_reason')})")
                min_cands = expected.get("expected_candidate_count_min", 0)
                if result["candidate_count"] < min_cands:
                    gs_fail.append(f"Expected >= {min_cands} candidates, got {result['candidate_count']}")
                if gs_fail:
                    result["gold_standard_failures"] = gs_fail
                    gold_standard_failures.append(
                        {
                            "domain": domain,
                            "slug": slug,
                            "failures": gs_fail,
                        }
                    )

            results.append(result)
            status_icon = "✓" if not result["is_fallback"] else "✗"
            print(
                f"  {status_icon} {domain}/{slug} — "
                f"candidates={result['candidate_count']} "
                f"winner={result['winner_source']} "
                f"time={result['total_time_sec']:.2f}s"
            )

    print(f"\nSnapshot Validation Complete: {len(results)}/{total_fixtures} fixtures tested.\n")

    # Report Gold Standard failures
    if gold_standard_failures:
        print("⚠️  GOLD STANDARD FAILURES:")
        for gsf in gold_standard_failures:
            print(f"   {gsf['domain']}/{gsf['slug']}:")
            for fail in gsf["failures"]:
                print(f"     - {fail}")
        print()

    # Generate reports
    summary = generate_report(results, "snapshot")

    # Exit with appropriate code
    if summary.get("status") == "PASS" and not gold_standard_failures:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_snapshots())
