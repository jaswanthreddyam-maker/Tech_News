from pydantic import BaseModel, Field

class ExplanationOutput(BaseModel):
    summary: str = Field(description="A concise 1-2 sentence summary of the incident and its resolution.")
    explanation: str = Field(description="A clear, human-readable narrative explaining what happened, strictly based on the provided evidence.")
    confidence_statement: str = Field(description="A statement explaining why the confidence score was given, referencing the specific evidence.")
    recommended_action: str = Field(description="Any recommended manual actions, or a confirmation that no action is needed if auto-resolved.")
