import logging
from typing import Any

from app.services.inference.models import InferenceRequest, PromptAsset

logger = logging.getLogger(__name__)

class InferenceGateway:
    """
    Abstracts LLM providers.
    Router -> Policy -> Guardrails -> Retry -> Fallback -> Cost Optimizer -> Provider.
    """
    def __init__(self, policy_engine: Any, provider_router: Any):
        self.policy_engine = policy_engine
        self.provider_router = provider_router
        self._prompts: dict[str, dict[str, PromptAsset]] = {}

    def register_prompt(self, asset: PromptAsset):
        if asset.name not in self._prompts:
            self._prompts[asset.name] = {}
        self._prompts[asset.name][asset.version] = asset
        logger.info(f"Registered Prompt Asset: {asset.name} v{asset.version}")

    async def execute(self, request: InferenceRequest) -> str:
        logger.info(f"InferenceGateway: Executing {request.prompt_asset_name} v{request.prompt_asset_version}")

        # 1. Fetch Prompt
        asset = self._prompts[request.prompt_asset_name][request.prompt_asset_version]

        # 2. Policy & Guardrails
        if self.policy_engine:
            decision = await self.policy_engine.execute(["LLM_SAFETY_POLICY"], request.context)
            if not decision.allowed:
                raise ValueError(f"Inference blocked by policy: {decision.reason}")

        # 3. Router -> Provider
        provider = self.provider_router.get_best_provider(asset)

        # 4. Execute with retry/fallback inside provider
        result = await provider.generate(asset, request.variables)
        return result
