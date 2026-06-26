from dataclasses import dataclass, field
from typing import Any


class ProjectionMutation:
    """Base class for all projection mutations"""
    pass

@dataclass
class IncrementMutation(ProjectionMutation):
    model: type
    target_id: str | int
    field: str
    amount: float | int

@dataclass
class SetMutation(ProjectionMutation):
    model: type
    target_id: str | int
    field: str
    value: Any

@dataclass
class InsertMutation(ProjectionMutation):
    model: type
    values: dict[str, Any]

@dataclass
class DeleteMutation(ProjectionMutation):
    model: type
    target_id: str | int

@dataclass
class AppendMutation(ProjectionMutation):
    model: type
    target_id: str | int
    field: str
    item: Any

@dataclass
class MergeMutation(ProjectionMutation):
    model: type
    target_id: str | int
    field: str
    data: dict[str, Any]

@dataclass
class UpsertMutation(ProjectionMutation):
    model: type
    target_id: str | int
    values: dict[str, Any]

@dataclass
class ProjectionBatch:
    version: int
    mutations: list[ProjectionMutation] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add(self, mutation: ProjectionMutation):
        self.mutations.append(mutation)
        return self
