from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shell import plan as shell_plan
from shell import runtime as shell_runtime


class RuntimeSkeletonTests(unittest.TestCase):
    def test_runtime_accepts_valid_execution_plan(self) -> None:
        runtime = shell_runtime.Runtime()
        plan = self.make_plan()
        result = runtime.accept_plan(plan, capabilities=("cap:home",))
        self.assertEqual(result, shell_runtime.RuntimeResult(
            status="accepted",
            step_count=2,
            dependency_count=1,
            capability_count=1,
        ))

    def test_runtime_returns_stable_placeholder_result(self) -> None:
        runtime = shell_runtime.Runtime()
        plan = self.make_plan()
        result = runtime.accept_plan(plan, capabilities=())
        self.assertEqual(result, shell_runtime.RuntimeResult(
            status="accepted",
            step_count=2,
            dependency_count=1,
            capability_count=0,
        ))

    def test_identical_plans_yield_identical_results(self) -> None:
        runtime = shell_runtime.Runtime()
        first = runtime.accept_plan(self.make_plan(), capabilities=("cap:home", "cap:net"))
        second = runtime.accept_plan(self.make_plan(), capabilities=("cap:home", "cap:net"))
        self.assertEqual(first, second)

    def make_plan(self) -> shell_plan.ExecutionPlan:
        return shell_plan.ExecutionPlan(
            steps=(
                shell_plan.Step(
                    step_id="step-0",
                    kind="binding",
                    statement_index=0,
                    pipeline_index=None,
                    binding_name="home",
                    target=None,
                    method=None,
                    value=shell_plan.PlanValue(kind="identifier", payload="root"),
                    arguments=(),
                ),
                shell_plan.Step(
                    step_id="step-1",
                    kind="invocation",
                    statement_index=1,
                    pipeline_index=None,
                    binding_name=None,
                    target="svc",
                    method="run",
                    value=None,
                    arguments=(),
                ),
            ),
            dependencies=(
                shell_plan.Dependency(
                    kind="program_statement_order",
                    from_step_id="step-0",
                    to_step_id="step-1",
                ),
            ),
        )


if __name__ == "__main__":
    unittest.main()
