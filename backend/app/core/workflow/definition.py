import logging

import yaml
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class WorkflowStageDef(BaseModel):
    name: str
    capabilities: list[str]
    parallel: bool = False

class WorkflowDefinition(BaseModel):
    """
    Declarative representation of a workflow.
    Aligns with ADR-0054: Workflows Are Declarative.
    """
    name: str
    version: str
    planner: str
    stages: list[WorkflowStageDef]

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "WorkflowDefinition":
        data = yaml.safe_load(yaml_content)
        return cls(**data)

class WorkflowDefinitionParser:
    def __init__(self):
        pass

    def parse_file(self, filepath: str) -> WorkflowDefinition:
        logger.info(f"Loading workflow definition from {filepath}")
        with open(filepath) as f:
            return WorkflowDefinition.from_yaml(f.read())
