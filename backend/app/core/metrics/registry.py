from prometheus_client import CollectorRegistry

# The central registry for Tech News Today metrics
REGISTRY = CollectorRegistry(auto_describe=True)
