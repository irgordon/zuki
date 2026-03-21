from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanValue:
    kind: str
    payload: object


@dataclass(frozen=True)
class PlanArgument:
    position: int
    kind: str
    value: PlanValue
    name: str | None = None


@dataclass(frozen=True)
class Step:
    step_id: str
    kind: str
    statement_index: int
    pipeline_index: int | None
    binding_name: str | None
    target: str | None
    method: str | None
    value: PlanValue | None
    arguments: tuple[PlanArgument, ...]


@dataclass(frozen=True)
class Dependency:
    kind: str
    from_step_id: str
    to_step_id: str


@dataclass(frozen=True)
class ExecutionPlan:
    steps: tuple[Step, ...]
    dependencies: tuple[Dependency, ...]
