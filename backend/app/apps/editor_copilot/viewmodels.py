
from pydantic import BaseModel


class DiffHunk(BaseModel):
    start_line: int
    end_line: int
    content: str

class FileDiff(BaseModel):
    file_path: str
    hunks: list[DiffHunk]

class CopilotResponseViewModel(BaseModel):
    """
    The UI never sees the OS artifacts directly. It only sees this ViewModel. (ADR-0076)
    """
    session_id: str
    status: str
    message: str
    diffs: list[FileDiff] | None = None
