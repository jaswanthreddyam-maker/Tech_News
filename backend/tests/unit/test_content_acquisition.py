import pytest
from app.services.ingestion.extraction_service import ExtractionResult
from app.services.ingestion.acquisition_policy import ContentAcquisitionPolicy


def test_substantive_rss_bypasses_canonical_extraction():
    policy = ContentAcquisitionPolicy(rss_substantive_threshold=100)
    rss_text = "Word " * 120  # 120 words
    decision = policy.evaluate("Test Title", rss_text, extraction_result=None)
    
    assert decision.decision == "RSS_SELECTED"
    assert decision.content_source == "rss_substantive"
    assert decision.word_count == 120
    assert decision.canonical_extraction_status == "BYPASSED_SUBSTANTIVE_RSS"
    assert decision.fallback_reason is None


def test_summary_only_rss_with_successful_canonical():
    policy = ContentAcquisitionPolicy(rss_substantive_threshold=100, canonical_substantive_threshold=150)
    rss_text = "Word " * 12  # 12 words
    extraction = ExtractionResult(
        status="SUCCESS",
        canonical_content="Full article body content " * 40,  # 160 words
        word_count=160,
        title="Canonical Title"
    )
    decision = policy.evaluate("RSS Title", rss_text, extraction_result=extraction)

    assert decision.decision == "CANONICAL_SELECTED"
    assert decision.content_source == "canonical_html"
    assert decision.word_count == 160
    assert decision.selected_title == "Canonical Title"
    assert decision.canonical_extraction_status == "SUCCESS"
    assert decision.fallback_reason is None


def test_openai_summary_only_rss_with_403_and_policy_deny():
    policy = ContentAcquisitionPolicy(rss_substantive_threshold=100)
    rss_text = "OpenAI explains recent third-party cyber evaluations."  # 7 words
    extraction = ExtractionResult(status="HTTP_403", word_count=0)
    
    source_policy = {"allow_weak_rss_fallback": False}
    decision = policy.evaluate("OpenAI Post", rss_text, extraction_result=extraction, source_policy=source_policy)

    assert decision.decision == "REJECTED"
    assert decision.content_source == "none"
    assert decision.word_count == 0
    assert decision.canonical_extraction_status == "HTTP_403"
    assert decision.fallback_reason == "CANONICAL_HTTP_403_WEAK_RSS"


def test_summary_only_rss_with_insufficient_canonical():
    policy = ContentAcquisitionPolicy(rss_substantive_threshold=100, canonical_substantive_threshold=150)
    rss_text = "Short RSS summary text."  # 4 words
    extraction = ExtractionResult(status="SUCCESS", canonical_content="Short page", word_count=37)

    source_policy = {"allow_weak_rss_fallback": False}
    decision = policy.evaluate("Short Title", rss_text, extraction_result=extraction, source_policy=source_policy)

    assert decision.decision == "REJECTED"
    assert decision.content_source == "none"
    assert decision.canonical_extraction_status == "SUCCESS"
    assert decision.fallback_reason == "CANONICAL_CONTENT_INSUFFICIENT_WEAK_RSS"


def test_weak_rss_with_allowed_fallback_policy():
    policy = ContentAcquisitionPolicy(rss_substantive_threshold=100)
    rss_text = "Short RSS summary text."
    extraction = ExtractionResult(status="HTTP_403", word_count=0)

    source_policy = {"allow_weak_rss_fallback": True}
    decision = policy.evaluate("Allowed Source Title", rss_text, extraction_result=extraction, source_policy=source_policy)

    assert decision.decision == "RSS_FALLBACK_SELECTED"
    assert decision.content_source == "rss_fallback"
    assert decision.selected_content == rss_text
    assert decision.canonical_extraction_status == "HTTP_403"
    assert decision.fallback_reason == "CANONICAL_HTTP_403_WEAK_RSS"
