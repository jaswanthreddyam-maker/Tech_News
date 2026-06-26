from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.intelligence.schemas import SearchQuery, SearchResponse
from app.intelligence.search.pipeline import HybridSearchPipeline
from app.models.user import User

router = APIRouter()

@router.post("/search", response_model=SearchResponse)
async def search(query: SearchQuery, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    pipeline = HybridSearchPipeline()

    # Map API filters to pipeline filters
    filters = query.filters.copy()
    if query.workspace_id:
        filters["workspace_id"] = query.workspace_id

    results = await pipeline.execute(
        db=db,
        query=query.query,
        filters=filters,
        limit=query.limit
    )

    return SearchResponse(
        query=query.query,
        results=results,
        total_results=len(results)
    )

from app.intelligence.generation.capabilities.base import CapabilityRegistry
from app.intelligence.generation.capabilities.implementations import (
    EditorialCapability,
    RAGCapability,
    SummaryCapability,
)
from app.intelligence.generation.context import CapabilityContext
from app.intelligence.generation.schemas import GenerationRequest, GenerationResponse

# Global capability registry
capability_registry = CapabilityRegistry()
capability_registry.register(SummaryCapability())
capability_registry.register(RAGCapability())
capability_registry.register(EditorialCapability())

async def execute_capability(request: GenerationRequest, capability_name: str, db: AsyncSession) -> GenerationResponse:
    context = CapabilityContext(
        capability_name=capability_name,
        query=request.query,
        workspace_id=request.workspace_id,
        filters=request.filters,
        conversation_history=request.conversation_history
    )

    capability = capability_registry.get(capability_name)
    result = await capability.execute(db, context, stream=request.stream)
    return result

@router.post("/summarize", response_model=GenerationResponse)
async def summarize_endpoint(request: GenerationRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await execute_capability(request, "SummaryCapability", db)

@router.post("/rag", response_model=GenerationResponse)
async def rag_endpoint(request: GenerationRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await execute_capability(request, "RAGCapability", db)

@router.post("/editorial", response_model=GenerationResponse)
async def editorial_endpoint(request: GenerationRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await execute_capability(request, "EditorialCapability", db)
