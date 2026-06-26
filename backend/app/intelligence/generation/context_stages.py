from app.intelligence.generation.context import AIContext


class ContextCollector:
    """Collects chunks from all configured retrievers (already executed by pipeline)."""
    def execute(self, context: AIContext) -> AIContext:
        # In this architecture, pipeline performs retrieval and populates context.retrieved_chunks.
        # This stage could perform initial validation.
        return context

class ContextDeduplicator:
    """Removes identical or heavily overlapping chunks retrieved from different sources."""
    def execute(self, context: AIContext) -> AIContext:
        seen = set()
        deduped = []
        for chunk in context.retrieved_chunks:
            # Simple identity dedup
            cid = chunk.get("source_id")
            if cid and cid not in seen:
                seen.add(cid)
                deduped.append(chunk)
            elif not cid:
                deduped.append(chunk)
        context.retrieved_chunks = deduped
        return context

class ContextCompressor:
    """Compresses or reranks chunks before allocation."""
    def execute(self, context: AIContext) -> AIContext:
        # Stub for cross-encoder or simple truncation
        context.compressed_chunks = context.retrieved_chunks[:20]
        return context

class TokenBudgetAllocator:
    """Ensures final chunks fit within the provider's max_context window."""
    def __init__(self, max_tokens: int = 8192):
        self.max_tokens = max_tokens

    def execute(self, context: AIContext) -> AIContext:
        # Stub logic for token truncation
        current_tokens = 0
        final_chunks = []
        for chunk in context.compressed_chunks:
            # Approximate 4 chars per token
            tokens = len(chunk.get("content", "")) // 4
            if current_tokens + tokens <= self.max_tokens:
                final_chunks.append(chunk)
                current_tokens += tokens
            else:
                break
        context.compressed_chunks = final_chunks
        return context
