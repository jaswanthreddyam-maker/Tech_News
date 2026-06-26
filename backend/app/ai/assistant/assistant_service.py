import json
import logging
import os
from collections.abc import AsyncGenerator

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.assistant.default_tools import register_default_tools
from app.ai.assistant.tools import AssistantToolRegistry
from app.ai.chat.stream_service import StreamService
from app.core.config import settings

logger = logging.getLogger("tech_news.ai.assistant")


class PersonalAssistantService:
    def __init__(self, db: AsyncSession):
        self.db = db
        api_key = getattr(settings, "OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
        self.client = AsyncOpenAI(api_key=api_key) if api_key else None
        self.model = getattr(settings, "CHAT_MODEL", "gpt-4o-mini")

        self.registry = AssistantToolRegistry()
        register_default_tools(self.registry)

    async def stream_query(self, query: str, owner_type: str, owner_id: str) -> AsyncGenerator[str, None]:
        if not self.client:
            yield StreamService.format_error("AI provider not configured")
            return

        system_prompt = (
            "You are a Personal AI Research Assistant. You are an orchestrator that manages "
            "the user's knowledge base. You have access to tools to search their notes, read their "
            "workspaces, check daily digests, and more.\n\n"
            "Use the provided tools to gather information before answering. You may use up to 5 tools "
            "in a row to build context. When you have enough context, synthesize a clear, helpful answer."
        )

        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": query}]

        tools_schema = self.registry.get_all_tools_schema()

        # We allow up to 5 iterations of tool calling
        max_iterations = 5

        for iteration in range(max_iterations):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools_schema if tools_schema else None,
                    tool_choice="auto" if tools_schema else "none",
                )
            except Exception as e:
                logger.error(f"Assistant LLM error: {e}")
                yield StreamService.format_error("Provider error during orchestration")
                return

            msg = response.choices[0].message

            # If no tool calls, we are done planning and just need to stream the final generation
            if not msg.tool_calls:
                # We need to stream the final answer instead of just returning the bulk message
                # So we make one final streaming call with the accumulated messages
                break

            # Execute tool calls
            # Append assistant message with tool_calls
            assistant_msg = {
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in msg.tool_calls
                ],
            }
            messages.append(assistant_msg)

            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    kwargs = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    kwargs = {}

                # Emit to UI that a tool is being used
                yield f"event: tool_started\ndata: {json.dumps({'tool': name, 'args': kwargs})}\n\n"

                # Execute
                result_str = await self.registry.execute_tool(
                    name=name, kwargs=kwargs, db=self.db, owner_type=owner_type, owner_id=owner_id
                )

                yield f"event: tool_result\ndata: {json.dumps({'tool': name})}\n\n"

                messages.append({"role": "tool", "tool_call_id": tc.id, "name": name, "content": result_str})

        # Final generation stream
        try:
            stream = await self.client.chat.completions.create(model=self.model, messages=messages, stream=True)
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    text_chunk = chunk.choices[0].delta.content
                    yield f"event: assistant_token\ndata: {json.dumps({'text': text_chunk})}\n\n"

            yield "event: completed\ndata: {}\n\n"

        except Exception as e:
            logger.error(f"Assistant generation error: {e}")
            yield StreamService.format_error("Generation failed")
