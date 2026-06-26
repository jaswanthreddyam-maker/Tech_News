import logging
from typing import Any

logger = logging.getLogger(__name__)

class BaseAdapter:
    async def execute_infrastructure(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError()

class AdapterFactory:
    """
    Instantiates the correct adapter implementation for a given capability at runtime.
    Ensures that infrastructure dependencies never leak upward.
    """
    def __init__(self):
        self._adapters: dict[str, type[BaseAdapter]] = {}

    def register_adapter(self, name: str, adapter_cls: type[BaseAdapter]):
        self._adapters[name] = adapter_cls
        logger.info(f"Registered Adapter: {name}")

    def get_adapter(self, name: str) -> BaseAdapter:
        if name not in self._adapters:
            raise ValueError(f"Adapter {name} not found.")
        return self._adapters[name]()
