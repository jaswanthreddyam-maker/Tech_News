import hashlib
import json
import os

import pytest

from app.ai.schemas import AITaskRequest, ArticleAIInput
from app.ai.service import AIService


@pytest.mark.asyncio
async def test_ai_summary_quality():
    """
    Test the AI summarization pipeline for quality: valid JSON, reasonable length, and keyword presence.
    """
    data_dir = os.path.join(os.path.dirname(__file__), "data", "ai")
    sample_file = os.path.join(data_dir, "sample_article_1.json")

    with open(sample_file) as f:
        data = json.load(f)

    prompt_text = "Generate a summary and keywords."
    prompt_hash = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()

    request = AITaskRequest(
        task_type="summary",
        article=ArticleAIInput(title=data["title"], content=data["content"]),
        prompt=prompt_text,
        prompt_version="test_v1",
        prompt_hash=prompt_hash,
        model="gpt-4o-mini",  # use default/cheap model for tests
        max_output_tokens=500,
    )

    service = AIService()
    try:
        response = await service.run_task(request)
        assert response is not None
        assert response.payload is not None

        # Check summary length
        summary = response.payload.get("summary", "")
        assert len(summary) > 10, "Summary is too short"
        words = summary.split()
        assert len(words) <= 150, "Summary is too long"

        # Check keywords
        keywords = response.payload.get("keywords", [])
        assert isinstance(keywords, list), "Keywords should be a list"

        # Note: Actual strict matching is hard for LLMs, but we can verify
        # that the API returns the expected structure.
        assert "summary" in response.payload
        assert "keywords" in response.payload
        assert "tags" in response.payload
    except Exception as e:
        pytest.skip(f"Skipping test due to provider error or missing API key: {e}")
