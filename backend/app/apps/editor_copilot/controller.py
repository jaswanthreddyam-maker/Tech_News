from fastapi import APIRouter, Depends

from app.apps.editor_copilot.application import EditorCopilotApplication
from app.apps.editor_copilot.schemas import CopilotRequest
from app.apps.editor_copilot.viewmodels import CopilotResponseViewModel

router = APIRouter()

# In a real app, EditorCopilotApplication is injected via Depends
def get_editor_copilot() -> EditorCopilotApplication:
    # return container.resolve(EditorCopilotApplication)
    return EditorCopilotApplication()

@router.post("/copilot/intent", response_model=CopilotResponseViewModel)
async def submit_intent(
    request: CopilotRequest,
    copilot: EditorCopilotApplication = Depends(get_editor_copilot)
):
    """
    Entrypoint for Editor IDEs to submit intent to the AI OS.
    """
    return await copilot.process_intent(request)
