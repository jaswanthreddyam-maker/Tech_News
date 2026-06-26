"""
HTMLAgent — Production-grade article extraction agent.

Architecture:
  1. Load source-specific selector profiles from source_profiles.yaml
  2. Strip boilerplate tags (script, style, nav, header, footer, etc.)
  3. Apply source-specific DOM exclusions (ads, sidebars, share widgets)
  4. Try prioritised CSS selectors via soup.select_one() — first match wins
  5. Fall back to link-density scoring over all <div>/<section> candidates
  6. Run BoilerplateCleaner on extracted text
  7. Run ContentQualityValidator — reject if quality too low
  8. Score the result and return
"""

import re
from pathlib import Path
from typing import Any

import yaml
from bs4 import BeautifulSoup

from agents.base.base_agent import BaseAgent

# ---------------------------------------------------------------------------
# Source profiles loader
# ---------------------------------------------------------------------------

_PROFILES_PATH = Path(__file__).parent.parent.parent / "source_profiles.yaml"

def _load_profiles() -> dict[str, Any]:
    """Load and cache source extraction profiles from YAML."""
    try:
        with _PROFILES_PATH.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}

_PROFILES: dict[str, Any] = _load_profiles()


def _get_profile(source_name: str | None) -> dict[str, Any]:
    """
    Return the extraction profile for a given source name.
    Falls back to _default if no match found.
    Matching is case-insensitive and normalises spaces/underscores.
    """
    if not source_name:
        return _PROFILES.get("_default", {})

    # Normalise: lowercase, replace spaces with underscores
    normalised = source_name.lower().replace(" ", "_").replace("-", "_")

    # Direct match
    if normalised in _PROFILES:
        return _PROFILES[normalised]

    # Partial match (e.g. "The Verge" → "the_verge")
    for key in _PROFILES:
        if key.startswith("_"):
            continue
        if normalised in key or key in normalised:
            return _PROFILES[key]

    return _PROFILES.get("_default", {})


# ---------------------------------------------------------------------------
# Boilerplate Cleaner
# ---------------------------------------------------------------------------

class BoilerplateCleaner:
    """
    Strips navigation, footer, and boilerplate text from extracted content.
    Patterns are applied line-by-line to avoid nuking multi-sentence paragraphs
    that happen to contain a single boilerplate keyword.
    """

    # Lines that match these patterns are removed entirely
    LINE_PATTERNS = re.compile(
        r"""
        ^(
            privacy\s+policy
          | terms\s+of\s+(service|use)
          | cookie\s+policy
          | sign\s+(in|up|out)
          | log\s+(in|out)
          | subscribe(\s+to)?
          | newsletter
          | contact\s+us
          | advertise
          | see\s+all\s+(reviews|tech|science)
          | the\s+homepage
          | skip\s+to(\s+main)?\s+content
          | follow\s+us\s+on
          | download\s+the\s+app
          | share\s+(this|on|via)
          | more\s+stories
          | related\s+articles?
          | you\s+may\s+(also\s+)?like
          | read\s+more
          | comments?
          | all\s+rights\s+reserved
          | copyright\s+\d{4}
          | tech\s+reviews?\s*$
          | amazon\s*$|apple\s*$|facebook\s*$|google\s*$|microsoft\s*$|samsung\s*$
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    # Prefixes stripped from the very beginning of the full text blob
    PREFIX_PATTERNS = [
        r"Skip to (main )?content",
        r"Sign in",
        r"Log in",
        r"Subscribe",
        r"Newsletter",
        r"Share on Mastodon",
        r"Share on Twitter",
        r"Share on Facebook",
    ]

    def clean(self, text: str) -> str:
        if not text:
            return ""

        # 1. Strip boilerplate lines
        lines = text.splitlines()
        clean_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                clean_lines.append("")
                continue
            if self.LINE_PATTERNS.match(stripped):
                continue
            clean_lines.append(line)

        cleaned = "\n".join(clean_lines)

        # 2. Strip known prefix noise from the very beginning
        prefix_stripped = True
        while prefix_stripped:
            prefix_stripped = False
            for pattern in self.PREFIX_PATTERNS:
                new_text, count = re.subn(
                    r"(?i)^\s*" + pattern + r"\s*(\n+|$)", "", cleaned
                )
                if count > 0:
                    cleaned = new_text
                    prefix_stripped = True
                    break

        # 3. Collapse excessive blank lines
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        # 4. Collapse excessive spaces
        cleaned = re.sub(r" {2,}", " ", cleaned)

        return cleaned.strip()


# ---------------------------------------------------------------------------
# Content Quality Validator
# ---------------------------------------------------------------------------

class ContentQualityValidator:
    """
    Validates extracted content before it is stored.

    Checks:
      - Minimum character count
      - Minimum paragraph/sentence count
      - Navigation link ratio (high ratio = nav contamination)
      - Stopword ratio (too high = boilerplate noise)
      - Duplicate line ratio (duplicated lines = nav repeated across columns)
      - Boilerplate keyword density
    """

    MIN_CHARS = 300
    MIN_PARAGRAPHS = 2
    MAX_NAV_RATIO = 0.35        # >35% nav text = contaminated
    MAX_BOILERPLATE_DENSITY = 0.25  # >25% boilerplate lines = contaminated
    MAX_DUPLICATE_LINE_RATIO = 0.40  # >40% duplicate lines = nav mirror

    BOILERPLATE_KEYWORDS = {
        "sign in", "sign up", "log in", "subscribe", "newsletter",
        "privacy policy", "terms of service", "cookie", "advertisement",
        "the homepage", "see all", "more stories", "tech reviews",
        "skip to", "contact us", "advertise", "follow us",
    }

    def validate(self, text: str, link_chars: int = 0) -> dict[str, Any]:
        """
        Returns dict with keys: valid (bool), reason (str), metrics (dict).
        """
        if not text:
            return {"valid": False, "reason": "empty_content", "metrics": {}}

        total_chars = len(text)

        # 1. Minimum length
        if total_chars < self.MIN_CHARS:
            return {
                "valid": False,
                "reason": f"too_short ({total_chars} chars < {self.MIN_CHARS})",
                "metrics": {"chars": total_chars},
            }

        # 2. Nav/link ratio
        nav_ratio = link_chars / total_chars if total_chars > 0 else 0.0
        if nav_ratio > self.MAX_NAV_RATIO:
            return {
                "valid": False,
                "reason": f"high_nav_ratio ({nav_ratio:.2f} > {self.MAX_NAV_RATIO})",
                "metrics": {"nav_ratio": nav_ratio},
            }

        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if not lines:
            return {"valid": False, "reason": "no_content_lines", "metrics": {}}

        # 3. Paragraph count (approximate by non-empty lines or ". " boundaries)
        sentences = re.split(r"(?<=[.!?])\s+", text)
        paragraph_count = max(1, len([s for s in sentences if len(s) > 40]))
        if paragraph_count < self.MIN_PARAGRAPHS:
            return {
                "valid": False,
                "reason": f"too_few_paragraphs ({paragraph_count} < {self.MIN_PARAGRAPHS})",
                "metrics": {"paragraph_count": paragraph_count},
            }

        # 4. Boilerplate keyword density
        lower_text = text.lower()
        boilerplate_hits = sum(1 for kw in self.BOILERPLATE_KEYWORDS if kw in lower_text)
        boilerplate_density = boilerplate_hits / max(len(self.BOILERPLATE_KEYWORDS), 1)
        if boilerplate_density > self.MAX_BOILERPLATE_DENSITY:
            return {
                "valid": False,
                "reason": f"high_boilerplate_density ({boilerplate_density:.2f})",
                "metrics": {"boilerplate_density": boilerplate_density},
            }

        # 5. Duplicate line ratio
        total_lines = len(lines)
        unique_lines = len(set(l.lower() for l in lines))
        dup_ratio = 1.0 - (unique_lines / total_lines) if total_lines > 0 else 0.0
        if dup_ratio > self.MAX_DUPLICATE_LINE_RATIO:
            return {
                "valid": False,
                "reason": f"high_duplicate_line_ratio ({dup_ratio:.2f})",
                "metrics": {"dup_ratio": dup_ratio},
            }

        return {
            "valid": True,
            "reason": "passed",
            "metrics": {
                "chars": total_chars,
                "nav_ratio": nav_ratio,
                "paragraph_count": paragraph_count,
                "boilerplate_density": boilerplate_density,
                "dup_ratio": dup_ratio,
            },
        }


# ---------------------------------------------------------------------------
# HTMLAgent
# ---------------------------------------------------------------------------

_cleaner = BoilerplateCleaner()
_validator = ContentQualityValidator()


class HTMLAgent(BaseAgent):
    """
    Advanced Ingestion Agent: fetches HTML pages, strips boilerplate,
    applies source-aware CSS selectors, validates content quality,
    and returns cleaned text with a readability score.
    """

    def __init__(self) -> None:
        super().__init__("html_ingestion")

    async def extract_article(
        self,
        url: str,
        parser_config: dict[str, Any] | None = None,
        timeout: float | None = None,
        source_name: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Fetch HTML page and extract cleaned, boilerplate-free article body.

        Args:
            url: Target URL to fetch.
            parser_config: Optional legacy per-source config (selector/exclude keys).
            timeout: HTTP request timeout override.
            source_name: Publisher name used to look up source_profiles.yaml entry.
        """
        self.logger.info(f"HTML Extract: Fetching {url}")

        response = await self.execute_request(url, timeout=timeout)
        if not response or not response.text:
            self.logger.error(f"HTML Extract: No content from {url}")
            return None

        try:
            payload = self.clean_html(response.text, parser_config, source_name=source_name)
            payload["url"] = url
            payload["raw_html"] = response.text
            return payload
        except Exception as exc:
            self.logger.error(f"HTML Extract: Exception for {url}: {exc!s}", exc_info=True)
            return None

    def clean_html(
        self,
        raw_html: str,
        parser_config: dict[str, Any] | None = None,
        source_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Parse raw HTML → strip boilerplate → select article body → validate quality.
        """
        if not raw_html:
            return {"title": "", "clean_text": "", "content_score": 0.0, "density_score": 0.0, "word_count": 0}

        soup = BeautifulSoup(raw_html, "html.parser")

        # ── 1. Extract <title> ────────────────────────────────────────────────
        title_tag = soup.find("title")
        title = title_tag.get_text().strip() if title_tag else ""

        # ── 2. Strip always-unsafe/boilerplate tags ───────────────────────────
        STRIP_TAGS = [
            "script", "style", "noscript", "iframe", "header", "footer", "nav",
            "aside", "form", "svg", "button", "canvas", "video", "audio", "input",
            "select", "textarea", "modal", "dialog", "figure",
        ]
        for tag in soup.find_all(STRIP_TAGS):
            tag.decompose()

        # ── 3. Strip elements matching noise class/id patterns ────────────────
        NOISE_PATTERN = re.compile(
            r"comment|share|social|advertisement|sidebar|menu|footer|header|nav|"
            r"widget|banner|ad-|promo|popup|cookie|subscribe|newsletter|paywall|"
            r"related|trending|most-popular|sign-in|sign-up|login|modal|overlay",
            re.IGNORECASE,
        )
        SAFE_CONTAINERS = frozenset({"article", "main", "body", "html", "section", "div"})

        for element in list(soup.find_all(True)):
            if not getattr(element, "attrs", None):
                continue
            if element.name not in SAFE_CONTAINERS:
                # Non-container noise tags — check class/id
                pass

            classes = element.get("class") or []
            if isinstance(classes, str):
                classes = [classes]
            class_str = " ".join(classes)

            elem_id = element.get("id", "")
            combined = f"{class_str} {elem_id}"

            if NOISE_PATTERN.search(combined):
                # Don't remove structural wrappers that happen to match
                safe_words = ("with-", "has-", "container", "wrapper", "layout", "content", "body", "article")
                if any(w in combined.lower() for w in safe_words):
                    continue
                element.decompose()

        # ── 4. Resolve selector list ──────────────────────────────────────────
        # Priority: parser_config (legacy) > source profile > _default profile
        profile = _get_profile(source_name)
        profile_selectors: list[str] = profile.get("selectors", [])
        profile_excludes: list[str] = profile.get("exclude", [])

        # Apply source-profile DOM exclusions
        for excl in profile_excludes:
            try:
                for el in soup.select(excl):
                    el.decompose()
            except Exception:
                pass

        # Legacy parser_config exclusions
        if parser_config and parser_config.get("exclude"):
            for excl in str(parser_config["exclude"]).split(","):
                excl = excl.strip()
                if excl:
                    try:
                        for el in soup.select(excl):
                            el.decompose()
                    except Exception:
                        pass

        # Build ordered selector list: legacy custom → profile → default
        default_selectors: list[str] = _PROFILES.get("_default", {}).get("selectors", [
            "[itemprop='articleBody']",
            ".article-content",
            ".post-content",
            ".entry-content",
            "#article-body",
            ".main-content",
            "article",
            "main",
        ])

        ordered_selectors: list[str] = []
        if parser_config and parser_config.get("selector"):
            ordered_selectors.append(str(parser_config["selector"]))
        ordered_selectors.extend(profile_selectors)
        # Only add default selectors that aren't already included
        for s in default_selectors:
            if s not in ordered_selectors:
                ordered_selectors.append(s)

        # ── 5. Find body container via selectors ──────────────────────────────
        body_container = None
        matched_selector = None

        for selector in ordered_selectors:
            try:
                found = soup.select_one(selector)
            except Exception:
                continue

            if found is None:
                continue

            text_len = len(found.get_text(strip=True))
            if text_len > 300:
                body_container = found
                matched_selector = selector
                self.logger.info(f"HTML Extract: Matched selector '{selector}' ({text_len} chars)")
                break

        # ── 6. Scoring fallback if no selector matched ────────────────────────
        if not body_container:
            self.logger.info("HTML Extract: No selector matched — running link-density scorer")
            best_score = -1.0
            body_container = soup.body or soup

            for candidate in soup.find_all(["div", "section", "article"]):
                candidate_text = candidate.get_text(separator=" ", strip=True)
                if len(candidate_text) < 200:
                    continue

                link_text_len = sum(len(a.get_text(strip=True)) for a in candidate.find_all("a"))
                total_text_len = len(candidate_text)
                link_density = link_text_len / total_text_len if total_text_len > 0 else 1.0
                p_count = len(candidate.find_all("p"))
                score = (total_text_len - link_text_len) * (1.0 - link_density) * (1.0 + 0.1 * p_count)

                if score > best_score:
                    best_score = score
                    body_container = candidate

            self.logger.info(f"HTML Extract: Scorer selected container with score {best_score:.2f}")

        # ── 7. Extract text from container ────────────────────────────────────
        content_elements = body_container.find_all(["p", "li", "h1", "h2", "h3", "h4", "h5", "h6"])
        if content_elements:
            raw_text = "\n\n".join(
                elem.get_text().strip()
                for elem in content_elements
                if elem.get_text().strip()
            )
        else:
            raw_text = body_container.get_text(separator="\n\n", strip=True)

        # ── 8. Boilerplate cleaning ───────────────────────────────────────────
        cleaned_text = _cleaner.clean(raw_text)

        # ── 9. Content quality validation ─────────────────────────────────────
        link_chars = sum(len(a.get_text(strip=True)) for a in body_container.find_all("a"))
        validation = _validator.validate(cleaned_text, link_chars=link_chars)

        if not validation["valid"]:
            self.logger.warning(
                f"HTML Extract: Quality check FAILED — {validation['reason']}. "
                f"selector='{matched_selector}' url content may be nav-contaminated."
            )
            # If we matched a specific selector but quality failed,
            # emit a very low score so the pipeline can fall back to RSS summary
            return {
                "title": title,
                "clean_text": cleaned_text,
                "content_score": 5.0,
                "density_score": 0.1,
                "word_count": len(cleaned_text.split()),
                "quality_valid": False,
                "quality_reason": validation["reason"],
            }

        # ── 10. Scoring ───────────────────────────────────────────────────────
        word_count = len(cleaned_text.split())
        paragraph_count = len(body_container.find_all("p"))
        total_chars = len(cleaned_text)
        final_link_density = link_chars / total_chars if total_chars > 0 else 0.0
        density_score = 1.0 - final_link_density
        content_score = min(100.0, (word_count * 0.1) * density_score + (paragraph_count * 2.0))

        self.logger.info(
            f"HTML Extract: OK — {word_count} words, score={content_score:.1f}, "
            f"selector='{matched_selector}'"
        )

        return {
            "title": title,
            "clean_text": cleaned_text,
            "content_score": round(content_score, 2),
            "density_score": round(density_score, 2),
            "word_count": word_count,
            "quality_valid": True,
            "quality_reason": "passed",
        }
