import asyncio

from app.services.ingestion.filter import compute_title_similarity, evaluate_adaptive_quality
from app.services.ingestion.utils import resolve_redirects


async def test_redirect_resolver():
    print("--- 1. Testing Resilient Redirect Resolution ---")
    urls = [
        "https://t.co/w2sF2JpB4q",  # Twitter shortener mock redirect
        "http://techcrunch.com",
    ]
    for url in urls:
        resolved = await resolve_redirects(url)
        print(f"Original: {url} -> Resolved: {resolved}")


def test_title_similarity():
    print("\n--- 2. Testing Cheap-Checks-First Soft title Similarity ---")
    pairs = [
        ("OpenAI unveils GPT-5", "GPT-5 officially announced by OpenAI", True),
        ("OpenAI unveils GPT-5", "OpenAI announces new search engine", False),
        ("NVIDIA launches Blackwell chips - TechCrunch", "NVIDIA launches Blackwell chips", True),
    ]
    for t1, t2, expected in pairs:
        score = compute_title_similarity(t1, t2)
        print(
            f"Title 1: '{t1}'\nTitle 2: '{t2}'\nSimilarity Score: {score:.3f} (Match: {score >= 0.75}, Expected: {expected})\n"
        )


def test_adaptive_quality():
    print("\n--- 3. Testing Adaptive Quality Scoring & Truncation Detection ---")
    # Authentic flash (short but high quality)
    flash_content = (
        "OpenAI announced a critical security patch for its API endpoints. "
        "The vulnerability was discovered by internal security teams and could have allowed "
        "unauthorized prompt injection. Users are advised to update their system integrations immediately."
    )
    flash_res = evaluate_adaptive_quality(
        title="OpenAI Security Update",
        content=flash_content,
        raw_html="<p>" + flash_content + "</p>",
        meta_dict={"source_category": "official"},
    )
    print(
        f"Flash Article: Eligible: {flash_res['eligible']}, Confidence: {flash_res['confidence']}%, Reason: {flash_res.get('reason', 'N/A')}"
    )

    # Truncated snippet
    truncated_content = (
        "OpenAI announced a critical security patch for its API endpoints. "
        "The vulnerability was discovered by... read more"
    )
    truncated_res = evaluate_adaptive_quality(
        title="OpenAI Security Update",
        content=truncated_content,
        raw_html="<p>" + truncated_content + "</p>",
        meta_dict={"source_category": "official"},
    )
    print(
        f"Truncated Article: Eligible: {truncated_res['eligible']}, Confidence: {truncated_res['confidence']}%, Reason: {truncated_res.get('reason', 'N/A')}"
    )


async def run_all():
    await test_redirect_resolver()
    test_title_similarity()
    test_adaptive_quality()


if __name__ == "__main__":
    asyncio.run(run_all())
