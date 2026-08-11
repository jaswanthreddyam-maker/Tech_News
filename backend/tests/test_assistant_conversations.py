import json
import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from app.ai.assistant.assistant_service import PersonalAssistantService, ASSISTANT_MAX_CONTEXT_MESSAGES
from app.api.v1.routes.assistant import _verify_session_owner, query_assistant, get_assistant_conversation, list_assistant_conversations, AssistantQueryRequest
from app.models.conversation import ConversationSession
from app.models.memory import ConversationEpisode
from app.ai.chat.schemas import OwnerType


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Override database setup fixture for fast, isolated unit tests."""
    yield


@pytest.mark.asyncio
async def test_session_owner_verification():
    """Test 2 & 11: Ownership verification helper logic."""
    session = ConversationSession(
        conversation_id="conv_100",
        user_id=123,
        metadata_json={"owner_type": "user", "owner_id": "123"}
    )
    assert _verify_session_owner(session, OwnerType.USER, "123") is True
    assert _verify_session_owner(session, OwnerType.USER, "999") is False


@pytest.mark.asyncio
async def test_cross_owner_conversation_rejected():
    """Test 3: Cross-owner session access must raise 404 HTTP Exception."""
    mock_db = AsyncMock()
    other_session = ConversationSession(
        conversation_id="conv_secret",
        user_id=999,
        metadata_json={"owner_type": "user", "owner_id": "999"}
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = other_session
    mock_db.execute.return_value = mock_result

    # Expect HTTP 404 when user "123" requests "conv_secret"
    with pytest.raises(HTTPException) as exc_info:
        await get_assistant_conversation("conv_secret", (OwnerType.USER, "123"), mock_db)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Conversation not found"


@pytest.mark.asyncio
async def test_context_chronological_ordering():
    """Test 10: History episodes must be injected in chronological order (oldest -> newest)."""
    mock_db = AsyncMock()
    service = PersonalAssistantService(db=mock_db)

    ep1 = ConversationEpisode(
        conversation_id="conv_chron",
        role="user",
        message="Message 1 (Oldest)",
        created_at=datetime(2026, 8, 10, 10, 0, 0, tzinfo=timezone.utc)
    )
    ep2 = ConversationEpisode(
        conversation_id="conv_chron",
        role="assistant",
        message="Message 2 (Newer)",
        created_at=datetime(2026, 8, 10, 10, 1, 0, tzinfo=timezone.utc)
    )
    
    mock_res = MagicMock()
    mock_res.scalars().all.return_value = [ep1, ep2]
    mock_db.execute.return_value = mock_res

    # Intercept LLM create call to verify prompt structure
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.tool_calls = None
    mock_response.choices[0].message.content = "Answer"

    async def mock_stream_chunks():
        chunk = MagicMock()
        chunk.choices = [MagicMock()]
        chunk.choices[0].delta.content = "Response"
        yield chunk

    async def mock_create(**kwargs):
        if kwargs.get("stream"):
            return mock_stream_chunks()
        return mock_response

    mock_client.chat.completions.create = AsyncMock(side_effect=mock_create)
    service.client = mock_client

    events = []
    async for event in service.stream_query("Message 3 (Current)", "user", "123", conversation_id="conv_chron"):
        events.append(event)

    # Verify LLM call received messages in chronological order
    first_call_messages = mock_client.chat.completions.create.call_args_list[0].kwargs["messages"]
    assert first_call_messages[1]["content"] == "Message 1 (Oldest)"
    assert first_call_messages[2]["content"] == "Message 2 (Newer)"
    assert first_call_messages[3]["content"] == "Message 3 (Current)"


@pytest.mark.asyncio
async def test_session_and_sources_sse_events():
    """Test 5, 6, 12: SSE events carry message_id correlation and normalized sources."""
    mock_db = AsyncMock()
    service = PersonalAssistantService(db=mock_db)

    # Tool call output for search_global_tech_news
    tool_result_json = json.dumps([
        {
            "title": "NVIDIA Blackwell GPUs",
            "source": "TechCrunch",
            "url": "https://example.com/blackwell",
            "snippet": "NVIDIA announced new architecture.",
            "relevance_score": 0.98
        }
    ])

    tc = MagicMock()
    tc.id = "tc_1"
    tc.type = "function"
    tc.function.name = "search_global_tech_news"
    tc.function.arguments = json.dumps({"query": "NVIDIA"})

    res1 = MagicMock()
    res1.choices = [MagicMock()]
    res1.choices[0].message.tool_calls = [tc]

    async def mock_stream_chunks():
        chunk = MagicMock()
        chunk.choices = [MagicMock()]
        chunk.choices[0].delta.content = "Analysis completed."
        yield chunk

    call_count = 0
    async def mock_create(**kwargs):
        nonlocal call_count
        if kwargs.get("stream"):
            return mock_stream_chunks()
        call_count += 1
        if call_count == 1:
            return res1
        no_tool = MagicMock()
        no_tool.choices = [MagicMock()]
        no_tool.choices[0].message.tool_calls = None
        return no_tool

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=mock_create)
    service.client = mock_client

    with patch("app.ai.chat.retrieval.RetrievalEngine.retrieve", new_callable=AsyncMock) as mock_ret:
        mock_ret.return_value = [
            {
                "type": "article",
                "id": 1,
                "title": "NVIDIA Blackwell GPUs",
                "content": "NVIDIA announced new architecture.",
                "url": "https://example.com/blackwell",
                "score": 0.98
            }
        ]

        events = []
        async for event in service.stream_query("NVIDIA news", "user", "123", conversation_id="conv_test_123", message_id="msg_fixed_100"):
            events.append(event)

        # Assert session event
        session_events = [e for e in events if e.startswith("event: session")]
        assert len(session_events) == 1
        session_data = json.loads(session_events[0].replace("event: session\ndata: ", ""))
        assert session_data["conversation_id"] == "conv_test_123"
        assert session_data["message_id"] == "msg_fixed_100"

        # Assert sources event correlated with message_id
        sources_events = [e for e in events if e.startswith("event: sources")]
        assert len(sources_events) == 1
        sources_data = json.loads(sources_events[0].replace("event: sources\ndata: ", ""))
        assert sources_data["message_id"] == "msg_fixed_100"
        assert len(sources_data["sources"]) == 1
        assert sources_data["sources"][0]["title"] == "NVIDIA Blackwell GPUs"
        assert sources_data["sources"][0]["url"] == "https://example.com/blackwell"


@pytest.mark.asyncio
async def test_retry_deduplication():
    """Test 13: Retrying query re-uses session without duplicating user message in context."""
    mock_db = AsyncMock()
    ep_user = ConversationEpisode(conversation_id="conv_retry", role="user", message="Retry Query", created_at=datetime.now(timezone.utc))
    
    mock_res = MagicMock()
    mock_res.scalars().all.return_value = [ep_user]
    mock_db.execute.return_value = mock_res

    service = PersonalAssistantService(db=mock_db)
    
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.tool_calls = None

    async def mock_stream():
        c = MagicMock()
        c.choices = [MagicMock()]
        c.choices[0].delta.content = "Retried Answer"
        yield c

    async def mock_create(**kwargs):
        if kwargs.get("stream"):
            return mock_stream()
        return mock_response

    mock_client.chat.completions.create = AsyncMock(side_effect=mock_create)
    service.client = mock_client

    events = []
    async for event in service.stream_query("Retry Query", "user", "123", conversation_id="conv_retry"):
        events.append(event)

    messages_sent = mock_client.chat.completions.create.call_args_list[0].kwargs["messages"]
    user_msgs = [m for m in messages_sent if m["role"] == "user"]
    # Only 1 user message should be sent (deduplicated against existing DB query episode)
    assert len(user_msgs) == 1
    assert user_msgs[0]["content"] == "Retry Query"


@pytest.mark.asyncio
async def test_critical_multi_turn_integration():
    """Test 15: Critical multi-turn integration (Turn 1 -> Turn 2 maintains context)."""
    mock_db = AsyncMock()
    service = PersonalAssistantService(db=mock_db)

    # Turn 1: User asks about NVIDIA
    ep_turn1_user = ConversationEpisode(conversation_id="conv_multi", role="user", message="What happened with NVIDIA recently?", created_at=datetime(2026, 8, 10, 10, 0, 0, tzinfo=timezone.utc))
    ep_turn1_ast = ConversationEpisode(conversation_id="conv_multi", role="assistant", message="NVIDIA announced the Blackwell GPU architecture.", created_at=datetime(2026, 8, 10, 10, 0, 5, tzinfo=timezone.utc))

    mock_res = MagicMock()
    mock_res.scalars().all.return_value = [ep_turn1_user, ep_turn1_ast]
    mock_db.execute.return_value = mock_res

    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.tool_calls = None

    async def mock_stream():
        c = MagicMock()
        c.choices = [MagicMock()]
        c.choices[0].delta.content = "This is important because it boosts AI speed."
        yield c

    async def mock_create(**kwargs):
        if kwargs.get("stream"):
            return mock_stream()
        return mock_response

    mock_client.chat.completions.create = AsyncMock(side_effect=mock_create)
    service.client = mock_client

    # Turn 2: User asks "Why is that important?"
    events = []
    async for event in service.stream_query("Why is that important?", "user", "123", conversation_id="conv_multi"):
        events.append(event)

    messages_sent = mock_client.chat.completions.create.call_args_list[0].kwargs["messages"]
    
    # Assert Turn 2 LLM prompt includes Turn 1 user and assistant context
    assert any(m["role"] == "user" and "What happened with NVIDIA" in m["content"] for m in messages_sent)
    assert any(m["role"] == "assistant" and "Blackwell GPU" in m["content"] for m in messages_sent)
    assert messages_sent[-1]["role"] == "user"
    assert messages_sent[-1]["content"] == "Why is that important?"


@pytest.mark.asyncio
async def test_simple_greeting_does_not_invoke_tools():
    """Verify that a simple greeting ('Hi') bypasses LLM tool creation and RAG tool orchestration."""
    mock_db = AsyncMock()
    service = PersonalAssistantService(db=mock_db)

    mock_client = AsyncMock()
    service.client = mock_client

    events = []
    async for event in service.stream_query("Hi", "user", "123"):
        events.append(event)

    # Verify LLM tool orchestrator create method was NEVER called
    mock_client.chat.completions.create.assert_not_called()
    # Verify tool events were not emitted
    assert not any("event: tool_started" in e for e in events)


@pytest.mark.asyncio
async def test_simple_greeting_returns_user_facing_text_only():
    """Verify simple greeting returns clean user-facing response."""
    mock_db = AsyncMock()
    service = PersonalAssistantService(db=mock_db)

    events = []
    async for event in service.stream_query("Hello!", "user", "123"):
        events.append(event)

    tokens = [json.loads(e.replace("event: assistant_token\ndata: ", ""))["text"] for e in events if e.startswith("event: assistant_token")]
    full_response = "".join(tokens)
    assert "Hello!" in full_response or "explore today" in full_response
    assert "orchestrator" not in full_response.lower()
    assert "we need to greet" not in full_response.lower()


@pytest.mark.asyncio
async def test_internal_instruction_not_exposed_in_assistant_stream():
    """Verify internal reasoning_content from model chunks is NEVER leaked to assistant_token."""
    mock_db = AsyncMock()
    service = PersonalAssistantService(db=mock_db)

    # Chunk with internal reasoning_content and user-facing content
    async def mock_stream():
        c1 = MagicMock()
        c1.choices = [MagicMock()]
        c1.choices[0].delta.content = None
        c1.choices[0].delta.reasoning_content = "INTERNAL MODEL THINKING: We need to greet the user..."
        yield c1

        c2 = MagicMock()
        c2.choices = [MagicMock()]
        c2.choices[0].delta.content = "NVIDIA announced new GPUs."
        c2.choices[0].delta.reasoning_content = None
        yield c2

    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.tool_calls = None

    async def mock_create(**kwargs):
        if kwargs.get("stream"):
            return mock_stream()
        return mock_response

    mock_client.chat.completions.create = AsyncMock(side_effect=mock_create)
    service.client = mock_client

    events = []
    async for event in service.stream_query("Tell me about NVIDIA", "user", "123"):
        events.append(event)

    tokens = [json.loads(e.replace("event: assistant_token\ndata: ", ""))["text"] for e in events if e.startswith("event: assistant_token")]
    accumulated_text = "".join(tokens)
    
    # Assert user-facing content is present
    assert "NVIDIA announced new GPUs." in accumulated_text
    # Assert internal reasoning_content is NOT in the stream
    assert "INTERNAL MODEL THINKING" not in accumulated_text
    assert "greet the user" not in accumulated_text


@pytest.mark.asyncio
async def test_research_query_still_uses_orchestrator():
    """Verify research query still invokes full LLM tool orchestrator."""
    mock_db = AsyncMock()
    service = PersonalAssistantService(db=mock_db)

    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.tool_calls = None

    async def mock_stream():
        c = MagicMock()
        c.choices = [MagicMock()]
        c.choices[0].delta.content = "Research findings..."
        yield c

    async def mock_create(**kwargs):
        if kwargs.get("stream"):
            return mock_stream()
        return mock_response

    mock_client.chat.completions.create = AsyncMock(side_effect=mock_create)
    service.client = mock_client

    events = []
    async for event in service.stream_query("What happened with NVIDIA recently?", "user", "123"):
        events.append(event)

    # Assert orchestrator create method was called
    assert mock_client.chat.completions.create.call_count >= 1
    assert any("event: completed" in e for e in events)


@pytest.mark.asyncio
async def test_assistant_tokens_stream_incrementally():
    """Verify tokens stream incrementally chunk by chunk."""
    mock_db = AsyncMock()
    service = PersonalAssistantService(db=mock_db)

    async def mock_stream():
        for chunk_text in ["Chunk 1 ", "Chunk 2 ", "Chunk 3"]:
            c = MagicMock()
            c.choices = [MagicMock()]
            c.choices[0].delta.content = chunk_text
            yield c

    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.tool_calls = None

    async def mock_create(**kwargs):
        if kwargs.get("stream"):
            return mock_stream()
        return mock_response

    mock_client.chat.completions.create = AsyncMock(side_effect=mock_create)
    service.client = mock_client

    events = []
    async for event in service.stream_query("Detailed query", "user", "123"):
        events.append(event)

    token_events = [e for e in events if e.startswith("event: assistant_token")]
    assert len(token_events) == 3
    assert "Chunk 1 " in token_events[0]
    assert "Chunk 2 " in token_events[1]
    assert "Chunk 3" in token_events[2]

