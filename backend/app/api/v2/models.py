from enum import Enum

from pydantic import BaseModel


class OperationStatus(str, Enum):
    """
    Public lifecycle of an Operation. Hides internal Goal states.
    """
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Operation(BaseModel):
    """
    The API primitive tracking a request.
    Internal Goal ID is hidden.
    """
    operation_id: str
    status: OperationStatus = OperationStatus.CREATED
    artifact_id: str | None = None
    message: str | None = None

class IntentSchema(BaseModel):
    """
    External representation of a Goal request.
    """
    action: str
    target: str
    context: dict | None = None
