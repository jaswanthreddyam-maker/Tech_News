from typing import ClassVar

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.growth import RuntimeConfiguration


class GenerationProfile(BaseModel):
    name: str
    provider: str = "mock"
    model: str = "mock-model"
    temperature: float = 0.0
    max_tokens: int = 4096
    stream: bool = False
    json_mode: bool = False
    tool_choice: str = "auto"
    retry_policy: str = "default"

class ProfileLoader:
    """
    Loads Generation Profiles dynamically from the Growth Platform's Runtime Configuration.
    Allows production tuning of AI models without deployment.
    """

    # Fallbacks if DB has no config
    FALLBACKS: ClassVar[dict] = {
        "Fast": GenerationProfile(
            name="Fast",
            provider="openai",
            model="gpt-3.5-turbo",
            temperature=0.3,
            max_tokens=1024
        ),
        "Balanced": GenerationProfile(
            name="Balanced",
            provider="openai",
            model="gpt-4o",
            temperature=0.0,
            max_tokens=4096
        ),
        "Reasoning": GenerationProfile(
            name="Reasoning",
            provider="openai",
            model="o1-preview",
            temperature=1.0,
            max_tokens=8192
        ),
        "Mock": GenerationProfile(
            name="Mock",
            provider="mock",
            model="mock-model"
        )
    }

    @staticmethod
    async def load(db: AsyncSession, profile_name: str) -> GenerationProfile:
        # Load from RuntimeConfiguration
        # Example Key: generation_profile_fast
        key = f"generation_profile_{profile_name.lower()}"

        config = (await db.execute(
            select(RuntimeConfiguration).where(RuntimeConfiguration.key == key)
        )).scalar_one_or_none()

        if config and config.value:
            val = config.value
            return GenerationProfile(
                name=profile_name,
                provider=val.get("provider", "mock"),
                model=val.get("model", "mock-model"),
                temperature=val.get("temperature", 0.0),
                max_tokens=val.get("max_tokens", 4096),
                stream=val.get("stream", False),
                json_mode=val.get("json_mode", False),
                tool_choice=val.get("tool_choice", "auto"),
                retry_policy=val.get("retry_policy", "default")
            )

        return ProfileLoader.FALLBACKS.get(profile_name, ProfileLoader.FALLBACKS["Mock"])
