from app.intelligence.generation.capabilities.base import GenerationCapability
from app.intelligence.generation.prompt import PromptTemplate
from app.intelligence.generation.validation import CitationValidator


class SummaryCapability(GenerationCapability):
    @property
    def capability_name(self) -> str:
        return "SummaryCapability"

    def get_profile_name(self) -> str:
        return "Fast"

    def get_prompt_template(self) -> PromptTemplate:
        return PromptTemplate(
            system_prompt="You are a summarization assistant. Provide a concise summary of the text.",
            user_prompt="Please summarize the following: {query}"
        )

class RAGCapability(GenerationCapability):
    @property
    def capability_name(self) -> str:
        return "RAGCapability"

    def get_profile_name(self) -> str:
        return "Balanced"

    def get_prompt_template(self) -> PromptTemplate:
        return PromptTemplate(
            system_prompt="You are a helpful assistant answering questions based on retrieved context.",
            user_prompt="{query}"
        )

    def get_output_validators(self):
        # We enforce citation mapping for RAG
        return [CitationValidator()]

class EditorialCapability(GenerationCapability):
    @property
    def capability_name(self) -> str:
        return "EditorialCapability"

    def get_profile_name(self) -> str:
        return "Reasoning"

    def get_prompt_template(self) -> PromptTemplate:
        return PromptTemplate(
            system_prompt="You are an expert editorial copilot. Help rewrite or translate the text to match publication guidelines.",
            user_prompt="{query}"
        )
