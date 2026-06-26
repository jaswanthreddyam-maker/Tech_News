from pydantic import BaseModel

from app.ai.providers.chat import ChatMessage
from app.intelligence.generation.context import AIContext


class PromptTemplate(BaseModel):
    version: str = "v1"
    system_prompt: str
    developer_prompt: str | None = None
    context_prompt: str = "Context Information:\n{context_text}"
    memory_prompt: str | None = None
    user_prompt: str = "{query}"

class PromptBuilder:
    def __init__(self, template: PromptTemplate):
        self.template = template

    def build(self, context: AIContext) -> list[ChatMessage]:
        messages = []

        # System instructions
        if self.template.system_prompt:
            messages.append(ChatMessage(role="system", content=self.template.system_prompt))

        if self.template.developer_prompt:
            messages.append(ChatMessage(role="developer", content=self.template.developer_prompt))

        # Context block
        if context.compressed_chunks:
            context_text = "\n\n".join([
                f"[Citation ID: {c.get('source_id')}]\n{c.get('content')}"
                for c in context.compressed_chunks
            ])
            formatted_context = self.template.context_prompt.format(context_text=context_text)
            messages.append(ChatMessage(role="system", content=formatted_context))

        # Memory
        if self.template.memory_prompt and context.conversation_history:
            messages.append(ChatMessage(role="system", content=self.template.memory_prompt))

        # Prior conversation
        for msg in context.conversation_history:
            messages.append(ChatMessage(role=msg.get("role", "user"), content=msg.get("content", "")))

        # User query
        formatted_query = self.template.user_prompt.format(query=context.query)
        messages.append(ChatMessage(role="user", content=formatted_query))

        return messages
