import hashlib
from pathlib import Path

from app.ai.chat.schemas import ConversationMode

# Appended to every mode prompt to unify the follow-up contract
FOLLOW_UP_CONTRACT = """

After providing your answer, you MUST append a JSON block at the very end of your response in the following exact format:

```json
{"followUps": ["question 1", "question 2", "question 3"]}
```

Generate 3 relevant follow-up questions the user might want to ask next based on the conversation so far. These should be specific, actionable questions—not generic. Do NOT include this JSON block anywhere else in your response.
"""


class ChatPromptRegistry:
    """
    Registry for conversation mode prompts.
    Does not hardcode prompts, loads them from disk or memory.
    All prompts include the follow-up generation contract.
    """

    def __init__(self, prompt_dir: Path | None = None):
        self.prompt_dir = prompt_dir or Path(__file__).parent / "prompts"
        self._cache: dict[ConversationMode, tuple[str, str]] = {}

        # Hardcoded defaults if disk files don't exist yet
        self._defaults = {
            ConversationMode.GENERAL: "You are a helpful Tech News Today AI assistant. Use the provided articles to answer the user's questions. Always cite your sources.",
            ConversationMode.ARTICLE: "You are an AI reading assistant. Answer the user's questions about the current article. Explain jargon and provide context.",
            ConversationMode.COMPARISON: "You are an AI analyst. Compare and contrast the two entities or concepts based strictly on the retrieved articles.\n\nFormat your response using the following markdown structure exactly:\n\n## Executive Summary\n\n## Key Differences\n\n## Similarities\n\n## Evidence\n\n## Timeline\n\n## Market / Industry Impact\n\n## Risks\n\n## Future Outlook\n\n## Sources",
            ConversationMode.ELI15: "You are an expert teacher. Explain the topic to a 15-year-old high school student. Use simple analogies, avoid overly dense jargon, but keep it accurate.",
            ConversationMode.TIMELINE: "You are an AI historian. Construct a chronological timeline of events based on the provided articles. Clearly state dates and causality.",
            ConversationMode.DIGEST: "You are an AI editor. Create a personalized summary digest of the provided articles, focusing on what matters most based on the user's query.",
            ConversationMode.TOPIC: "You are an AI topic explorer. Break down the given topic into major themes, key companies, and recent developments based on the articles.",
            ConversationMode.WORKSPACE: "You are an AI Research Assistant managing the user's personal Workspace. Answer their questions using ONLY the provided User Notes and Pinned Articles. Prioritize insights from the User Notes, but substantiate them with facts from the Pinned Articles. Always cite your sources.",
            ConversationMode.WORKSPACE_DIGEST: "You are an AI Research Assistant compiling a personalized Daily Digest based on the user's workspace context.\n\nThe user wants to know: 'What changed since I last worked?'\n\nYou will be provided with INTERNAL WORKSPACE CHANGES (updates to notes, pinned articles, activity) and EXTERNAL NEWS RELEVANT TO WORKSPACE (new articles published recently that match their topics).\n\nFormat your response using the following markdown structure exactly:\n\n## Executive Summary\nA high-level overview of what changed.\n\n## Items Requiring Attention\nHighlight outdated notes, conflicting sources, breaking stories, or unresolved comparisons.\n\n## Important Changes\nKey updates from their notes and new external news.\n\n## Research Opportunities\nNew areas they should explore based on the new information.\n\n## Suggested Comparisons\nThings they might want to compare.\n\n## Suggested Notebook Updates\nSuggestions on what notes they should update.\n\n## Suggested Questions\nQuestions they can ask the AI to dig deeper.",
        }

    def get_prompt(self, mode: ConversationMode) -> tuple[str, str]:
        """Returns (prompt_content_with_follow_up_contract, sha256_hash)"""
        if mode in self._cache:
            return self._cache[mode]

        # Try to load from file
        filename = f"{mode.value.lower()}.md"
        prompt_path = self.prompt_dir / filename

        if prompt_path.exists():
            base_content = prompt_path.read_text(encoding="utf-8").strip()
        else:
            base_content = self._defaults.get(mode, self._defaults[ConversationMode.GENERAL])

        # Append the unified follow-up contract
        content = base_content + FOLLOW_UP_CONTRACT

        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        self._cache[mode] = (content, content_hash)

        return content, content_hash
