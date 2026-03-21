from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeResult:
    status: str
    step_count: int
    dependency_count: int
    capability_count: int
