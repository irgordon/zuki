from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shell import ast as shell_ast
from shell import plan as shell_plan


class ExecutionPlanTests(unittest.TestCase):
    def test_binding_only_program_converts_to_plan(self) -> None:
        plan = shell_plan.build_execution_plan(shell_ast.Program(statements=(
            shell_ast.Binding(
                name=shell_ast.Identifier(text="home"),
                value=shell_ast.IdentifierExpr(name=shell_ast.Identifier(text="root")),
            ),
        )))
        self.assertEqual(plan, shell_plan.ExecutionPlan(
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
            ),
            dependencies=(),
        ))

    def test_invocation_only_program_preserves_argument_order_and_distinction(self) -> None:
        plan = shell_plan.build_execution_plan(shell_ast.Program(statements=(
            shell_ast.Invocation(
                target=shell_ast.Identifier(text="svc"),
                method=shell_ast.Identifier(text="run"),
                args=(
                    shell_ast.PositionalArg(value=shell_ast.IntLiteral(value=1)),
                    shell_ast.NamedArg(
                        name=shell_ast.Identifier(text="mode"),
                        value=shell_ast.StringLiteral(value="fast"),
                    ),
                ),
            ),
        )))
        self.assertEqual(plan.steps[0].arguments, (
            shell_plan.PlanArgument(
                position=0,
                kind="positional",
                name=None,
                value=shell_plan.PlanValue(kind="int_literal", payload=1),
            ),
            shell_plan.PlanArgument(
                position=1,
                kind="named",
                name="mode",
                value=shell_plan.PlanValue(kind="string_literal", payload="fast"),
            ),
        ))

    def test_pipeline_program_converts_to_stage_steps_with_explicit_dependencies(self) -> None:
        plan = shell_plan.build_execution_plan(shell_ast.Program(statements=(
            shell_ast.Pipeline(stages=(
                shell_ast.Invocation(
                    target=shell_ast.Identifier(text="svc"),
                    method=shell_ast.Identifier(text="open"),
                    args=(),
                ),
                shell_ast.InvokeForm(
                    target=shell_ast.Identifier(text="inspect"),
                    method=shell_ast.Identifier(text="show"),
                    args=(),
                ),
                shell_ast.Invocation(
                    target=shell_ast.Identifier(text="audit"),
                    method=shell_ast.Identifier(text="record"),
                    args=(),
                ),
            )),
        )))
        self.assertEqual(plan, shell_plan.ExecutionPlan(
            steps=(
                shell_plan.Step(
                    step_id="step-0",
                    kind="invocation",
                    statement_index=0,
                    pipeline_index=0,
                    binding_name=None,
                    target="svc",
                    method="open",
                    value=None,
                    arguments=(),
                ),
                shell_plan.Step(
                    step_id="step-1",
                    kind="invoke_form",
                    statement_index=0,
                    pipeline_index=1,
                    binding_name=None,
                    target="inspect",
                    method="show",
                    value=None,
                    arguments=(),
                ),
                shell_plan.Step(
                    step_id="step-2",
                    kind="invocation",
                    statement_index=0,
                    pipeline_index=2,
                    binding_name=None,
                    target="audit",
                    method="record",
                    value=None,
                    arguments=(),
                ),
            ),
            dependencies=(
                shell_plan.Dependency(
                    kind="pipeline_stage_order",
                    from_step_id="step-0",
                    to_step_id="step-1",
                ),
                shell_plan.Dependency(
                    kind="pipeline_stage_order",
                    from_step_id="step-1",
                    to_step_id="step-2",
                ),
            ),
        ))

    def test_mixed_program_preserves_statement_order_and_dependencies(self) -> None:
        plan = shell_plan.build_execution_plan(shell_ast.Program(statements=(
            shell_ast.Binding(
                name=shell_ast.Identifier(text="home"),
                value=shell_ast.IdentifierExpr(name=shell_ast.Identifier(text="root")),
            ),
            shell_ast.Invocation(
                target=shell_ast.Identifier(text="svc"),
                method=shell_ast.Identifier(text="run"),
                args=(),
            ),
            shell_ast.Pipeline(stages=(
                shell_ast.Invocation(
                    target=shell_ast.Identifier(text="filter"),
                    method=shell_ast.Identifier(text="apply"),
                    args=(),
                ),
                shell_ast.Invocation(
                    target=shell_ast.Identifier(text="inspect"),
                    method=shell_ast.Identifier(text="show"),
                    args=(),
                ),
            )),
        )))
        self.assertEqual(plan.dependencies, (
            shell_plan.Dependency(
                kind="program_statement_order",
                from_step_id="step-0",
                to_step_id="step-1",
            ),
            shell_plan.Dependency(
                kind="program_statement_order",
                from_step_id="step-1",
                to_step_id="step-2",
            ),
            shell_plan.Dependency(
                kind="pipeline_stage_order",
                from_step_id="step-2",
                to_step_id="step-3",
            ),
        ))

    def test_identical_asts_yield_identical_plans(self) -> None:
        ast = shell_ast.Program(statements=(
            shell_ast.Binding(
                name=shell_ast.Identifier(text="name"),
                value=shell_ast.StringLiteral(value="value"),
            ),
            shell_ast.Invocation(
                target=shell_ast.Identifier(text="svc"),
                method=shell_ast.Identifier(text="run"),
                args=(
                    shell_ast.PositionalArg(value=shell_ast.BoolLiteral(value=True)),
                ),
            ),
        ))
        first = shell_plan.build_execution_plan(ast)
        second = shell_plan.build_execution_plan(ast)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
