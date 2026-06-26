
from pydantic import BaseModel


class EditorContext(BaseModel):
    file_path: str
    selection_start_line: int | None
    selection_end_line: int | None
    selected_text: str | None
    intent: str # e.g. "Refactor to Pure Function", "Add Unit Tests"

class CopilotRequest(BaseModel):
    session_id: str
    context: EditorContext
