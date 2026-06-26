from fastapi import APIRouter, Depends

from app.api.v2.models import IntentSchema, Operation
from app.api.v2.services.intent import IntentApplicationService

router = APIRouter(prefix="/intents", tags=["Enterprise Gateway"])

def get_current_enterprise_identity():
    # Stub: Authentication happens here, outside the kernel
    return "enterprise_service_account_123"

@router.post("/", response_model=Operation)
async def submit_intent(
    intent: IntentSchema,
    identity: str = Depends(get_current_enterprise_identity),
    intent_service: IntentApplicationService = Depends()
):
    """
    Translates an external Intent into an OS Operation.
    Controllers remain extremely thin.
    """
    return await intent_service.handle_intent(intent, identity)
