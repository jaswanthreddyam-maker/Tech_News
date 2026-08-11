import json
import pytest
from unittest.mock import AsyncMock, patch

from app.ai.assistant.tools import AssistantToolRegistry
from app.ai.assistant.default_tools import (
    register_default_tools,
    search_global_tech_news_executor,
)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Override database setup fixture for fast, isolated unit tests."""
    yield


@pytest.mark.asyncio
async def test_tool_registration():
    registry = AssistantToolRegistry()
    register_default_tools(registry)
    schemas = registry.get_all_tools_schema()
    
    tool_names = [s["function"]["name"] for s in schemas]
    assert "search_global_tech_news" in tool_names
    assert "search_my_knowledge" in tool_names
    assert "list_workspaces" in tool_names

    # Check search_global_tech_news schema details
    global_tool = next(s for s in schemas if s["function"]["name"] == "search_global_tech_news")
    assert "published Tech News Today" in global_tool["function"]["description"]
    assert "query" in global_tool["function"]["parameters"]["properties"]


@pytest.mark.asyncio
async def test_executor_bounded_formatting():
    mock_db = AsyncMock()
    mock_retrieved = [
        {
            "type": "article",
            "id": 101,
            "title": "NVIDIA Keynote 2026",
            "content": "A" * 500,  # 500 chars long
            "url": "https://example.com/nvidia-keynote",
            "score": 0.95,
        }
    ]

    with patch("app.ai.chat.retrieval.RetrievalEngine.retrieve", new_callable=AsyncMock) as mock_retrieve:
        mock_retrieve.return_value = mock_retrieved
        
        result = await search_global_tech_news_executor(query="NVIDIA", db=mock_db)
        
        mock_retrieve.assert_called_once_with(query="NVIDIA", db=mock_db, limit=3)
        assert "NVIDIA Keynote 2026" in result
        assert "https://example.com/nvidia-keynote" in result
        parsed = json.loads(result)
        assert parsed["title"] == "NVIDIA Keynote 2026"
        assert parsed["relevance_score"] == 0.95
        # Snippet should be bounded to 203 chars (200 + "...")
        assert len(parsed["snippet"]) <= 203
        assert parsed["snippet"].endswith("...")


@pytest.mark.asyncio
async def test_executor_empty_results():
    mock_db = AsyncMock()

    with patch("app.ai.chat.retrieval.RetrievalEngine.retrieve", new_callable=AsyncMock) as mock_retrieve:
        mock_retrieve.return_value = []
        
        result = await search_global_tech_news_executor(query="NonExistentTopic12345", db=mock_db)
        
        assert result == "No relevant articles were found in the Tech News corpus."


@pytest.mark.asyncio
async def test_executor_error_handling():
    mock_db = AsyncMock()

    with patch("app.ai.chat.retrieval.RetrievalEngine.retrieve", side_effect=RuntimeError("Vector DB disconnect")):
        with patch("app.ai.assistant.default_tools.logger.error") as mock_log:
            result = await search_global_tech_news_executor(query="ErrorTopic", db=mock_db)
            
            assert "An error occurred while searching global tech news articles." in result
            mock_log.assert_called_once()
            assert "Vector DB disconnect" in str(mock_log.call_args)


@pytest.mark.asyncio
async def test_personal_assistant_service_tool_loop():
    from app.ai.assistant.assistant_service import PersonalAssistantService
    from unittest.mock import MagicMock

    mock_db = AsyncMock()
    service = PersonalAssistantService(db=mock_db)

    # Create mock tool call structure
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_123"
    mock_tool_call.type = "function"
    mock_tool_call.function.name = "search_global_tech_news"
    mock_tool_call.function.arguments = json.dumps({"query": "NVIDIA GPUs"})

    # Iteration 1 response: requests tool execution
    mock_response_1 = MagicMock()
    mock_response_1.choices = [MagicMock()]
    mock_response_1.choices[0].message.tool_calls = [mock_tool_call]
    mock_response_1.choices[0].message.content = None

    # Final stream chunks generator
    async def mock_stream_chunks():
        chunk1 = MagicMock()
        chunk1.choices = [MagicMock()]
        chunk1.choices[0].delta.content = "NVIDIA has released "
        yield chunk1

        chunk2 = MagicMock()
        chunk2.choices = [MagicMock()]
        chunk2.choices[0].delta.content = "new AI chips."
        yield chunk2

    call_count = 0

    async def mock_create(**kwargs):
        nonlocal call_count
        if kwargs.get("stream"):
            return mock_stream_chunks()
        call_count += 1
        if call_count == 1:
            return mock_response_1

        no_tool_msg = MagicMock()
        no_tool_msg.choices = [MagicMock()]
        no_tool_msg.choices[0].message.tool_calls = None
        no_tool_msg.choices[0].message.content = "Synthesized answer"
        return no_tool_msg

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=mock_create)
    service.client = mock_client

    retrieved_article = [
        {
            "type": "article",
            "id": 1,
            "title": "NVIDIA Blackwell GPUs",
            "content": "NVIDIA announced new architecture.",
            "url": "https://example.com/blackwell",
            "score": 0.98,
        }
    ]

    with patch("app.ai.chat.retrieval.RetrievalEngine.retrieve", new_callable=AsyncMock) as mock_retrieve:
        mock_retrieve.return_value = retrieved_article

        events = []
        async for event in service.stream_query("What happened with NVIDIA recently?", "user", "123"):
            events.append(event)

        # Assert tool_started event emitted
        assert any("event: tool_started" in e and "search_global_tech_news" in e for e in events)
        # Assert tool_result event emitted
        assert any("event: tool_result" in e and "search_global_tech_news" in e for e in events)
        # Assert tokens streamed
        assert any("event: assistant_token" in e and "NVIDIA has released " in e for e in events)
        # Assert completion event
        assert any("event: completed" in e for e in events)
        # Assert retrieval engine was called
        # Fast-path calls retrieve directly with the raw user query and limit=3
        mock_retrieve.assert_called_once_with(query="What happened with NVIDIA recently?", db=mock_db, limit=3)


@pytest.mark.asyncio
async def test_routing_personal_query():
    """Test A: 'What do I know about NVIDIA?' must route to search_my_knowledge."""
    from app.ai.assistant.assistant_service import PersonalAssistantService
    from unittest.mock import MagicMock

    mock_db = AsyncMock()
    service = PersonalAssistantService(db=mock_db)

    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_personal"
    mock_tool_call.type = "function"
    mock_tool_call.function.name = "search_my_knowledge"
    mock_tool_call.function.arguments = json.dumps({"query": "NVIDIA"})

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.tool_calls = [mock_tool_call]
    mock_response.choices[0].message.content = None

    async def mock_stream_chunks():
        chunk = MagicMock()
        chunk.choices = [MagicMock()]
        chunk.choices[0].delta.content = "Based on your saved notes..."
        yield chunk

    call_count = 0
    async def mock_create(**kwargs):
        nonlocal call_count
        if kwargs.get("stream"):
            return mock_stream_chunks()
        call_count += 1
        if call_count == 1:
            return mock_response
        no_tool_msg = MagicMock()
        no_tool_msg.choices = [MagicMock()]
        no_tool_msg.choices[0].message.tool_calls = None
        return no_tool_msg

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=mock_create)
    service.client = mock_client

    events = []
    with patch("app.services.workspace_service.WorkspaceService.list_workspaces", new_callable=AsyncMock) as mock_ws:
        mock_ws.return_value = []
        async for event in service.stream_query("What do I know about NVIDIA?", "user", "123"):
            events.append(event)

    assert any("event: tool_started" in e and "search_my_knowledge" in e for e in events)


@pytest.mark.asyncio
async def test_routing_global_query():
    """Test B: 'What happened with NVIDIA recently?' must route to search_global_tech_news."""
    from app.ai.assistant.assistant_service import PersonalAssistantService
    from unittest.mock import MagicMock

    mock_db = AsyncMock()
    service = PersonalAssistantService(db=mock_db)

    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_global"
    mock_tool_call.type = "function"
    mock_tool_call.function.name = "search_global_tech_news"
    mock_tool_call.function.arguments = json.dumps({"query": "NVIDIA news"})

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.tool_calls = [mock_tool_call]
    mock_response.choices[0].message.content = None

    async def mock_stream_chunks():
        chunk = MagicMock()
        chunk.choices = [MagicMock()]
        chunk.choices[0].delta.content = "According to latest news..."
        yield chunk

    call_count = 0
    async def mock_create(**kwargs):
        nonlocal call_count
        if kwargs.get("stream"):
            return mock_stream_chunks()
        call_count += 1
        if call_count == 1:
            return mock_response
        no_tool_msg = MagicMock()
        no_tool_msg.choices = [MagicMock()]
        no_tool_msg.choices[0].message.tool_calls = None
        return no_tool_msg

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=mock_create)
    service.client = mock_client

    events = []
    with patch("app.ai.chat.retrieval.RetrievalEngine.retrieve", new_callable=AsyncMock) as mock_retrieve:
        mock_retrieve.return_value = []
        async for event in service.stream_query("What happened with NVIDIA recently?", "user", "123"):
            events.append(event)

    assert any("event: tool_started" in e and "search_global_tech_news" in e for e in events)


@pytest.mark.asyncio
async def test_routing_mixed_query():
    """Test C: Mixed query must invoke both search_my_knowledge and search_global_tech_news."""
    from app.ai.assistant.assistant_service import PersonalAssistantService
    from unittest.mock import MagicMock

    mock_db = AsyncMock()
    service = PersonalAssistantService(db=mock_db)

    # Iteration 1: search_my_knowledge
    tc1 = MagicMock()
    tc1.id = "call_mix_1"
    tc1.type = "function"
    tc1.function.name = "search_my_knowledge"
    tc1.function.arguments = json.dumps({"query": "NVIDIA"})

    res1 = MagicMock()
    res1.choices = [MagicMock()]
    res1.choices[0].message.tool_calls = [tc1]

    # Iteration 2: search_global_tech_news
    tc2 = MagicMock()
    tc2.id = "call_mix_2"
    tc2.type = "function"
    tc2.function.name = "search_global_tech_news"
    tc2.function.arguments = json.dumps({"query": "NVIDIA news"})

    res2 = MagicMock()
    res2.choices = [MagicMock()]
    res2.choices[0].message.tool_calls = [tc2]

    async def mock_stream_chunks():
        chunk = MagicMock()
        chunk.choices = [MagicMock()]
        chunk.choices[0].delta.content = "Comparing your notes with news..."
        yield chunk

    call_count = 0
    async def mock_create(**kwargs):
        nonlocal call_count
        if kwargs.get("stream"):
            return mock_stream_chunks()
        call_count += 1
        if call_count == 1:
            return res1
        if call_count == 2:
            return res2
        no_tool = MagicMock()
        no_tool.choices = [MagicMock()]
        no_tool.choices[0].message.tool_calls = None
        return no_tool

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=mock_create)
    service.client = mock_client

    events = []
    with patch("app.services.workspace_service.WorkspaceService.list_workspaces", new_callable=AsyncMock) as mock_ws:
        mock_ws.return_value = []
        with patch("app.ai.chat.retrieval.RetrievalEngine.retrieve", new_callable=AsyncMock) as mock_retrieve:
            mock_retrieve.return_value = []
            async for event in service.stream_query("What did I save about NVIDIA, and how does that compare with the latest news?", "user", "123"):
                events.append(event)

    tools_called = [json.loads(e.replace("event: tool_started\ndata: ", ""))["tool"] for e in events if e.startswith("event: tool_started")]
    assert "search_my_knowledge" in tools_called
    assert "search_global_tech_news" in tools_called


