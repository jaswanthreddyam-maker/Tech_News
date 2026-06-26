from fastapi import APIRouter

from app.api.v1.routes import (
    admin,
    ai_debug,
    ai_summary,
    articles,
    assistant,
    auth,
    behavioral,
    categories,
    certification,
    chat,
    cohorts,
    distribution,
    editorial,
    entities,
    events,
    experiments,
    funnels,
    growth,
    health,
    intelligence,
    news,
    personalization,
    recipients,
    recommendations,
    search,
    telemetry,
    topics,
    workspaces,
)
from app.newsletter.router import router as newsletter_router

from app.api.v1.routes import stories, lifecycle, calendar, admin_editorial, admin_events

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["System"])
api_router.include_router(events.router, prefix="/events", tags=["System"])
api_router.include_router(admin_editorial.router)
api_router.include_router(telemetry.router, prefix="/telemetry", tags=["System"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(admin_editorial.router)
api_router.include_router(admin_events.router)
api_router.include_router(stories.router, prefix="/stories", tags=["Stories"])
api_router.include_router(lifecycle.router, prefix="/lifecycle", tags=["Editorial Lifecycle"])
api_router.include_router(calendar.router, prefix="/calendar", tags=["Editorial Calendar"])
api_router.include_router(articles.router, prefix="/articles", tags=["Articles"])
api_router.include_router(certification.router, prefix="/certification", tags=["Certification"])
api_router.include_router(news.router, prefix="/news", tags=["News Feed"])
api_router.include_router(categories.router, prefix="/categories", tags=["Categories"])
api_router.include_router(topics.router, prefix="/topics", tags=["Topics"])
api_router.include_router(entities.router, prefix="/entities", tags=["Entities"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["Recommendations"])
api_router.include_router(behavioral.router, prefix="/behavioral", tags=["Behavioral"])
api_router.include_router(chat.router, prefix="/chat", tags=["AI Chat"])
api_router.include_router(ai_debug.router, prefix="/ai/debug", tags=["AI Core"])
api_router.include_router(ai_summary.router)
api_router.include_router(assistant.router, prefix="/assistant")
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["AI"])
api_router.include_router(personalization.router, prefix="/me", tags=["Personalization"])
api_router.include_router(editorial.router, prefix="/editorial", tags=["Editorial"])
api_router.include_router(distribution.router, prefix="/distribution", tags=["Distribution"])
api_router.include_router(recipients.router, prefix="/recipients", tags=["Recipients"])
api_router.include_router(growth.router, prefix="/growth", tags=["Growth"])
api_router.include_router(experiments.router, prefix="/experiments", tags=["Growth"])
api_router.include_router(funnels.router, prefix="/funnels", tags=["Growth"])
api_router.include_router(cohorts.router, prefix="/cohorts", tags=["Growth"])
api_router.include_router(intelligence.router, prefix="/intelligence", tags=["Intelligence"])
api_router.include_router(newsletter_router, prefix="/newsletter", tags=["Newsletter"])
