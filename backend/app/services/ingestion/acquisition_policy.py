"""
ContentAcquisitionPolicy — Deterministic Business Policy Authority for Article Content Selection.

Responsibility:
Evaluates rss_content and ExtractionResult against source policies to decide:
  1. Is RSS substantive (>100 words)? -> RSS_SELECTED
  2. If RSS insufficient, attempt canonical extraction via ExtractionService.
  3. Is Canonical extraction SUCCESS & substantive (>150 words)? -> CANONICAL_SELECTED
  4. If Canonical fails (403, 404, timeout, insufficient length):
     - Check source policy `allow_weak_rss_fallback` (Explicit source config, NEVER dynamically inferred!).
     - If ALLOWED -> RSS_FALLBACK_SELECTED
     - If DENIED -> REJECTED with composable fallback_reason (e.g. CANONICAL_403_WEAK_RSS, CANONICAL_CONTENT_INSUFFICIENT_WEAK_RSS)
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from app.services.ingestion.extraction_service import ExtractionResult


@dataclass
class AcquisitionDecision:
    content_source: str  # "canonical_html" | "rss_substantive" | "rss_fallback" | "none"
    decision: str        # "RSS_SELECTED" | "CANONICAL_SELECTED" | "RSS_FALLBACK_SELECTED" | "REJECTED"
    selected_content: str = ""
    selected_title: str = ""
    word_count: int = 0
    fallback_reason: Optional[str] = None
    rss_word_count: int = 0
    canonical_word_count: int = 0
    canonical_extraction_status: str = "NOT_ATTEMPTED"


class ContentAcquisitionPolicy:
    def __init__(
        self,
        rss_substantive_threshold: int = 100,
        canonical_substantive_threshold: int = 150,
    ):
        self.rss_substantive_threshold = rss_substantive_threshold
        self.canonical_substantive_threshold = canonical_substantive_threshold

    def evaluate(
        self,
        rss_title: str,
        rss_text: str,
        extraction_result: Optional[ExtractionResult],
        source_policy: Optional[Dict[str, Any]] = None,
    ) -> AcquisitionDecision:
        """
        Determines the canonical content selection and produces structured provenance.
        """
        source_cfg = source_policy or {}
        allow_weak_rss_fallback = bool(source_cfg.get("allow_weak_rss_fallback", False))
        rss_threshold = int(source_cfg.get("rss_substantive_threshold", self.rss_substantive_threshold))
        canonical_threshold = int(source_cfg.get("canonical_substantive_threshold", self.canonical_substantive_threshold))

        rss_words = len((rss_text or "").split())

        # Stage 1: Check if RSS is substantive enough to bypass canonical fetch
        if rss_words >= rss_threshold:
            return AcquisitionDecision(
                content_source="rss_substantive",
                decision="RSS_SELECTED",
                selected_content=rss_text,
                selected_title=rss_title,
                word_count=rss_words,
                fallback_reason=None,
                rss_word_count=rss_words,
                canonical_word_count=0,
                canonical_extraction_status="BYPASSED_SUBSTANTIVE_RSS",
            )

        # Stage 2: Evaluate Canonical Extraction Result (if attempted)
        if not extraction_result:
            return AcquisitionDecision(
                content_source="none",
                decision="REJECTED",
                fallback_reason="NO_EXTRACTION_ATTEMPTED_WEAK_RSS",
                rss_word_count=rss_words,
                canonical_word_count=0,
                canonical_extraction_status="NOT_ATTEMPTED",
            )

        canonical_status = extraction_result.status
        canonical_words = extraction_result.word_count
        canonical_text = extraction_result.canonical_content

        # Stage 3A: Canonical Extraction Succeeded & Passed Quality Gate
        if canonical_status == "SUCCESS" and canonical_words >= canonical_threshold:
            return AcquisitionDecision(
                content_source="canonical_html",
                decision="CANONICAL_SELECTED",
                selected_content=canonical_text,
                selected_title=extraction_result.title or rss_title,
                word_count=canonical_words,
                fallback_reason=None,
                rss_word_count=rss_words,
                canonical_word_count=canonical_words,
                canonical_extraction_status="SUCCESS",
            )

        # Stage 3B: Canonical Extraction Failed or Insufficient Length
        if canonical_status == "SUCCESS" and canonical_words < canonical_threshold:
            reason_code = "CANONICAL_CONTENT_INSUFFICIENT_WEAK_RSS"
        elif canonical_status in ("HTTP_403", "HTTP_404", "HTTP_429", "HTTP_5XX", "TIMEOUT", "EMPTY_BODY", "PARSER_FAILURE", "NETWORK_ERROR"):
            reason_code = f"CANONICAL_{canonical_status}_WEAK_RSS"
        else:
            reason_code = f"CANONICAL_FAILED_{canonical_status}_WEAK_RSS"

        # Stage 4: Check Source Policy for Weak RSS Fallback Permission
        if allow_weak_rss_fallback and rss_words > 0:
            return AcquisitionDecision(
                content_source="rss_fallback",
                decision="RSS_FALLBACK_SELECTED",
                selected_content=rss_text,
                selected_title=rss_title,
                word_count=rss_words,
                fallback_reason=reason_code,
                rss_word_count=rss_words,
                canonical_word_count=canonical_words,
                canonical_extraction_status=canonical_status,
            )

        # Stage 5: DENIED by Policy -> REJECTED
        return AcquisitionDecision(
            content_source="none",
            decision="REJECTED",
            selected_content="",
            selected_title=rss_title,
            word_count=0,
            fallback_reason=reason_code,
            rss_word_count=rss_words,
            canonical_word_count=canonical_words,
            canonical_extraction_status=canonical_status,
        )
