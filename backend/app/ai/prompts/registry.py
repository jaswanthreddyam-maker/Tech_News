
from typing import ClassVar


class PromptTemplate:
    def __init__(self, name: str, version: str, template: str):
        self.name = name
        self.version = version
        self.template = template

    def render(self, context_str: str) -> str:
        return self.template.replace("{{context}}", context_str)

class PromptTemplateRegistry:
    _templates: ClassVar[dict[str, PromptTemplate]] = {}

    @classmethod
    def register(cls, name: str, version: str, template: str):
        key = f"{name}:{version}"
        cls._templates[key] = PromptTemplate(name, version, template)

    @classmethod
    def get(cls, name: str, version: str = "v1") -> PromptTemplate:
        key = f"{name}:{version}"
        template = cls._templates.get(key)
        if not template:
            raise ValueError(f"Prompt Template {key} not found")
        return template

# Register a default Structured Summary Prompt
_SUMMARY_PROMPT = """
You are an expert tech news analyst. Your task is to generate a highly structured, objective, and evidence-backed summary of the provided context.
Ensure your response adheres strictly to the requested JSON schema.
For any timeline events, people, organizations, technologies, or takeaways you extract, you MUST provide citations mapping back to the source URL or source name provided in the context.

Context:
{{context}}
"""
PromptTemplateRegistry.register("SUMMARY", "v1", _SUMMARY_PROMPT)
