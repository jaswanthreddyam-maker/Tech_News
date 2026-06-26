from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DeliveryReportResponse(BaseModel):
    id: int
    job_id: int
    status: str
    attempt: int
    duration_ms: int | None
    error: str | None
    provider_response: dict[str, Any] | None
    metadata_info: dict[str, Any]
    started_at: datetime | None
    completed_at: datetime | None

    class Config:
        from_attributes = True

class DistributionJobResponse(BaseModel):
    id: int
    manifest_id: int
    subject_type: str
    subject_id: str
    channel: str
    status: str
    payload: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    reports: list[DeliveryReportResponse] = []

    class Config:
        from_attributes = True

class DistributionManifestResponse(BaseModel):
    id: int
    publication_record_id: int
    created_at: datetime
    jobs: list[DistributionJobResponse] = []

    class Config:
        from_attributes = True
