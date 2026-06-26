import logging
from typing import Any

from app.core.capability.models import CapabilityContract, CapabilityIdentity
from app.core.capability.registry import CapabilityInterface

logger = logging.getLogger(__name__)

class WebSearchCapability(CapabilityInterface):
    """
    Allows an agent to perform search engine queries.
    """
    @property
    def contract(self) -> CapabilityContract:
        return CapabilityContract(
            name="WEB_SEARCH",
            version="v1",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
            output_schema={"type": "object"},
            identity=CapabilityIdentity(identity_id="cap-websearch-1", owner="system")
        )

    async def execute(self, payload: dict[str, Any], context: Any) -> dict[str, Any]:
        query = payload.get("query", "")
        logger.info(f"WebSearchCapability: Searching for '{query}'")
        return {"results": [{"title": "Example Result", "url": "https://example.com"}]}

class BrowserSandboxCapability(CapabilityInterface):
    """
    Allows an agent to render and extract text from a webpage safely via SandboxCapability.
    """
    @property
    def contract(self) -> CapabilityContract:
        return CapabilityContract(
            name="BROWSER_SANDBOX",
            version="v1",
            input_schema={"type": "object", "properties": {"url": {"type": "string"}}},
            output_schema={"type": "object"},
            identity=CapabilityIdentity(identity_id="cap-browsersandbox-1", owner="system"),
            required_capabilities=["SANDBOX_EXECUTION"]
        )

    async def execute(self, payload: dict[str, Any], context: Any) -> dict[str, Any]:
        url = payload.get("url", "")
        logger.info(f"BrowserSandboxCapability: Safely rendering {url}")

        # In reality, this dispatches to the SANDBOX_EXECUTION capability

        return {"content": "Extracted text from the webpage."}
