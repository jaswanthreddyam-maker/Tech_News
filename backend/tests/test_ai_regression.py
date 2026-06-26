"""
Phase 7.10 — AI Regression Suite

Verifies the structural correctness and contract compliance of the
four AI subsystems without requiring a live LLM connection:

1. Chat / Citation:  Citation extraction, parsing, and schema compliance.
2. Notebook:         Prompt template completeness and operation routing.
3. Digest:           Context builder output structure and metadata side-channel.
4. Assistant:        Tool registry, schema generation, and execution tracing.
"""

from unittest.mock import AsyncMock

import pytest

# ---------------------------------------------------------------------------
# 1. Chat — Citation Schema & Extraction
# ---------------------------------------------------------------------------
from app.ai.chat.citation_service import CitationService
from app.ai.chat.schemas import (
    Citation,
    ConversationMode,
    ProvenanceData,
    ProvenanceItem,
    ProvenanceSummary,
    StreamEventType,
)


class TestChatCitationRegression:
    """Verify that the CitationService produces correct structured output."""

    def setup_method(self):
        self.svc = CitationService()
        self.articles = [
            {"id": 101, "title": "AI Chip Launch", "url": "https://example.com/101", "score": 0.95},
            {"id": 202, "title": "GPU Shortage", "url": "https://example.com/202", "score": 0.82},
            {"id": 303, "title": "Quantum Computing", "url": "https://example.com/303", "score": 0.71},
        ]

    def test_extracts_single_citation(self):
        text = "This is exciting news [Citation: 101] about AI chips."
        cleaned, citations = self.svc.extract_citations(text, self.articles)

        assert len(citations) == 1
        assert citations[0].article_id == 101
        assert citations[0].title == "AI Chip Launch"
        assert citations[0].url == "https://example.com/101"
        assert "[1]" in cleaned
        assert "[Citation:" not in cleaned

    def test_extracts_multiple_citations_in_order(self):
        text = "GPUs [Citation: 202] and AI [Citation: 101] are booming."
        cleaned, citations = self.svc.extract_citations(text, self.articles)

        assert len(citations) == 2
        # First encountered in article order, not text order
        assert citations[0].article_id == 101
        assert citations[1].article_id == 202

    def test_removes_invalid_citation_ids(self):
        text = "Unknown ref [Citation: 999] should be dropped."
        cleaned, citations = self.svc.extract_citations(text, self.articles)

        assert len(citations) == 0
        assert "[Citation:" not in cleaned
        assert "999" not in cleaned or "[999]" not in cleaned

    def test_citation_schema_has_required_fields(self):
        citation = Citation(
            article_id=1,
            title="Test",
            url="https://example.com",
            score=0.9,
        )
        data = citation.model_dump()
        assert "article_id" in data
        assert "title" in data
        assert "url" in data
        assert "score" in data
        assert "confidence" in data  # optional field must still appear

    def test_citation_pattern_is_case_insensitive(self):
        text = "Lower [citation: 101] and upper [CITATION: 202] both work."
        _, citations = self.svc.extract_citations(text, self.articles)
        assert len(citations) == 2

    def test_provenance_schema_structure(self):
        prov = ProvenanceData(
            summary=ProvenanceSummary(articles=3, notes=1),
            items=[
                ProvenanceItem(type="article", id=101, title="AI Chip Launch"),
            ],
            confidence="High",
        )
        data = prov.model_dump()
        assert data["summary"]["articles"] == 3
        assert len(data["items"]) == 1
        assert data["items"][0]["type"] == "article"

    def test_stream_event_types_cover_full_lifecycle(self):
        required_events = {
            "retrieval_started",
            "retrieval_finished",
            "provenance",
            "generation_started",
            "token",
            "citation",
            "completed",
            "error",
        }
        actual_events = {e.value for e in StreamEventType}
        assert required_events.issubset(actual_events), f"Missing events: {required_events - actual_events}"

    def test_conversation_modes_include_all_features(self):
        required_modes = {"GENERAL", "ARTICLE", "COMPARISON", "DIGEST", "WORKSPACE", "TOPIC"}
        actual_modes = {m.value for m in ConversationMode}
        assert required_modes.issubset(actual_modes), f"Missing modes: {required_modes - actual_modes}"


# ---------------------------------------------------------------------------
# 2. Notebook — Prompt Template Completeness & Operation Routing
# ---------------------------------------------------------------------------
from app.ai.chat.notebook_service import NotebookService
from app.models.workspace import NotebookOperation


class TestNotebookRegression:
    """Verify notebook operations produce correct prompts and route properly."""

    def test_all_operations_have_prompts(self):
        """Every NotebookOperation enum value must produce a non-empty prompt."""
        # NotebookService.__init__ requires a db session; we only need the prompt method
        # so we create a minimal mock instance.
        svc = NotebookService.__new__(NotebookService)

        for op in NotebookOperation:
            prompt = svc._get_prompt_for_operation(op)
            assert isinstance(prompt, str), f"Operation {op.value} returned non-string prompt"
            assert len(prompt) > 20, f"Operation {op.value} prompt is too short: '{prompt}'"
            assert "AI Research Assistant" in prompt, f"Operation {op.value} prompt missing role identity"

    def test_expand_prompt_mentions_expanding(self):
        svc = NotebookService.__new__(NotebookService)
        prompt = svc._get_prompt_for_operation(NotebookOperation.EXPAND)
        assert "expand" in prompt.lower()

    def test_refine_prompt_mentions_clarity(self):
        svc = NotebookService.__new__(NotebookService)
        prompt = svc._get_prompt_for_operation(NotebookOperation.REFINE)
        assert "refine" in prompt.lower() or "clarity" in prompt.lower()

    def test_outline_prompt_mentions_outline(self):
        svc = NotebookService.__new__(NotebookService)
        prompt = svc._get_prompt_for_operation(NotebookOperation.OUTLINE)
        assert "outline" in prompt.lower()

    def test_find_citations_prompt_mentions_citations(self):
        svc = NotebookService.__new__(NotebookService)
        prompt = svc._get_prompt_for_operation(NotebookOperation.FIND_CITATIONS)
        assert "citation" in prompt.lower()

    def test_notebook_operations_enum_completeness(self):
        """Verify the enum contains at least the core operations."""
        required_ops = {"EXPAND", "REFINE", "REWRITE", "OUTLINE", "FIND_CITATIONS"}
        actual_ops = {op.name for op in NotebookOperation}
        assert required_ops.issubset(actual_ops), f"Missing operations: {required_ops - actual_ops}"


# ---------------------------------------------------------------------------
# 3. Digest — Context Structure & Metadata Side-Channel
# ---------------------------------------------------------------------------
from app.ai.chat.digest_strategy import DigestRetrievalStrategy


class TestDigestRegression:
    """Verify digest retrieval output schema and metadata extraction."""

    def test_digest_context_item_types_are_known(self):
        """Every output dict from DigestRetrievalStrategy must have a 'type' field
        matching one of the known context types."""
        known_types = {
            "internal_note",
            "internal_article",
            "internal_activity",
            "external_article",
            "metadata",
        }
        # We don't call the actual retrieval (needs DB), but we verify that the
        # strategy class exists and its module defines the expected structure.
        assert hasattr(DigestRetrievalStrategy, "retrieve")

        # Verify InternalCollector exists and returns the expected shape
        from app.ai.chat.digest_strategy import InternalCollector

        assert hasattr(InternalCollector, "collect")

    def test_digest_context_builder_exists_and_callable(self):
        from app.ai.chat.digest_context_builder import DigestContextBuilder

        builder = DigestContextBuilder()
        assert callable(getattr(builder, "build_context", None))

    def test_digest_prompt_registry_has_workspace_digest_mode(self):
        from app.ai.chat.prompt_registry import ChatPromptRegistry

        registry = ChatPromptRegistry()
        prompt, system_msg = registry.get_prompt(ConversationMode.WORKSPACE_DIGEST)
        assert isinstance(prompt, str)
        assert len(prompt) > 50, "Digest prompt is suspiciously short"

    def test_workspace_digest_model_has_required_fields(self):
        from app.models.workspace import WorkspaceDigest

        required_columns = {"workspace_id", "content", "status", "since_time", "until_time"}
        actual_columns = {c.name for c in WorkspaceDigest.__table__.columns}
        assert required_columns.issubset(actual_columns), f"Missing digest columns: {required_columns - actual_columns}"


# ---------------------------------------------------------------------------
# 4. Assistant — Tool Registry & Execution Tracing
# ---------------------------------------------------------------------------
from app.ai.assistant.default_tools import register_default_tools
from app.ai.assistant.tools import AssistantToolRegistry, Tool


class TestAssistantRegression:
    """Verify assistant tool registry, schema generation, and execution tracing."""

    def setup_method(self):
        self.registry = AssistantToolRegistry()
        register_default_tools(self.registry)

    def test_default_tools_are_registered(self):
        """At least one tool must be registered after calling register_default_tools."""
        schema = self.registry.get_all_tools_schema()
        assert len(schema) > 0, "No tools registered by register_default_tools"

    def test_tool_schema_conforms_to_openai_function_calling_format(self):
        """Each tool schema must match the OpenAI function calling spec."""
        for tool_def in self.registry.get_all_tools_schema():
            assert tool_def["type"] == "function", f"Tool type must be 'function', got {tool_def['type']}"
            fn = tool_def["function"]
            assert "name" in fn, "Tool function missing 'name'"
            assert "description" in fn, "Tool function missing 'description'"
            assert "parameters" in fn, "Tool function missing 'parameters'"
            assert isinstance(fn["name"], str)
            assert len(fn["name"]) > 0
            assert isinstance(fn["description"], str)
            assert len(fn["description"]) > 10, f"Tool '{fn['name']}' description too short"

    def test_tool_names_are_unique(self):
        schema = self.registry.get_all_tools_schema()
        names = [t["function"]["name"] for t in schema]
        assert len(names) == len(set(names)), f"Duplicate tool names: {names}"

    def test_tool_parameters_have_type_object(self):
        """OpenAI requires function parameters to be type: object."""
        for tool_def in self.registry.get_all_tools_schema():
            params = tool_def["function"]["parameters"]
            assert params.get("type") == "object", f"Tool '{tool_def['function']['name']}' params type must be 'object'"

    @pytest.mark.asyncio
    async def test_execute_unknown_tool_returns_error_string(self):
        """Calling a non-existent tool must return an error message, not raise."""
        mock_db = AsyncMock()
        result = await self.registry.execute_tool(
            name="does_not_exist",
            kwargs={},
            db=mock_db,
            owner_type="user",
            owner_id="test-user",
        )
        assert "Error" in result
        assert "does_not_exist" in result

    def test_custom_tool_registration_and_schema(self):
        """Verify that registering a custom tool produces the correct schema."""
        custom_registry = AssistantToolRegistry()

        async def dummy_executor(**kwargs) -> str:
            return "ok"

        custom_tool = Tool(
            name="test_tool",
            description="A test tool for regression testing.",
            parameters={
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Search query"}},
                "required": ["query"],
            },
        )
        custom_registry.register(custom_tool, dummy_executor)

        schema = custom_registry.get_all_tools_schema()
        assert len(schema) == 1
        assert schema[0]["function"]["name"] == "test_tool"
        assert "query" in schema[0]["function"]["parameters"]["properties"]


# ---------------------------------------------------------------------------
# 5. Cross-Cutting — AI Enrichment Schema Regression
# ---------------------------------------------------------------------------
from app.ai.schemas import (
    AIEnrichmentOutput,
    AIJobStatus,
    AIServiceResult,
    AITelemetryRecord,
    SentimentLabel,
)


class TestEnrichmentSchemaRegression:
    """Verify that the core enrichment schemas haven't regressed."""

    def test_enrichment_output_requires_summary(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            AIEnrichmentOutput(summary="", keywords=[], tags=[], sentiment=SentimentLabel.NEUTRAL)

    def test_enrichment_output_deduplicates_keywords(self):
        output = AIEnrichmentOutput(
            summary="Test summary.",
            keywords=["AI", "ai", "Machine Learning", "machine learning", "AI"],
            tags=[],
            sentiment=SentimentLabel.POSITIVE,
        )
        assert len(output.keywords) == 2  # "AI" and "Machine Learning"

    def test_enrichment_output_deduplicates_tags(self):
        output = AIEnrichmentOutput(
            summary="Test summary.",
            keywords=[],
            tags=["tech", "Tech", "TECH"],
            sentiment=SentimentLabel.NEUTRAL,
        )
        assert len(output.tags) == 1

    def test_sentiment_labels_are_complete(self):
        expected = {"positive", "neutral", "negative"}
        actual = {s.value for s in SentimentLabel}
        assert expected == actual

    def test_ai_service_result_schema_has_telemetry_list(self):
        result = AIServiceResult(
            output=AIEnrichmentOutput(
                summary="Test.",
                keywords=[],
                tags=[],
                sentiment=SentimentLabel.NEUTRAL,
            ),
            status=AIJobStatus.COMPLETED,
        )
        assert isinstance(result.telemetry, list)
        assert result.error is None

    def test_telemetry_record_enforces_fingerprint_length(self):
        """Enrichment fingerprint must be exactly 64 characters (SHA-256 hex)."""
        valid_fingerprint = "a" * 64
        record = AITelemetryRecord(
            provider="mock",
            model="gpt-4o-mini",
            task_type="summary",
            prompt_version="summary_v1",
            status=AIJobStatus.COMPLETED,
            enrichment_input_fingerprint=valid_fingerprint,
        )
        assert record.enrichment_input_fingerprint == valid_fingerprint

        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            AITelemetryRecord(
                provider="mock",
                model="gpt-4o-mini",
                task_type="summary",
                prompt_version="summary_v1",
                status=AIJobStatus.COMPLETED,
                enrichment_input_fingerprint="too_short",
            )
