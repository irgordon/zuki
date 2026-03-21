from __future__ import annotations

from shell.plan import ExecutionPlan

from .model import RuntimeResult


class Runtime:
    def accept_plan(self, plan: ExecutionPlan, capabilities: tuple[object, ...]) -> RuntimeResult:
        if not isinstance(plan, ExecutionPlan):
            raise TypeError("plan must be an ExecutionPlan")
        return RuntimeResult(
            status="accepted",
            step_count=len(plan.steps),
            dependency_count=len(plan.dependencies),
            capability_count=len(capabilities),
        )
