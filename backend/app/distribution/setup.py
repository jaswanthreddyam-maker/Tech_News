from app.distribution.capabilities.email import EmailCapability
from app.distribution.capabilities.rss import RSSCapability
from app.distribution.registry import registry

_registered = False

def register_all_capabilities():
    global _registered
    if _registered:
        return

    registry.register(RSSCapability())
    registry.register(EmailCapability())
    _registered = True
