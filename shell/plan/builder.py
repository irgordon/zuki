from __future__ import annotations

from shell.ast import Binding
from shell.ast import BoolLiteral
from shell.ast import IdentifierExpr
from shell.ast import IntLiteral
from shell.ast import Invocation
from shell.ast import InvokeForm
from shell.ast import ListExpr
from shell.ast import NamedArg
from shell.ast import NullLiteral
from shell.ast import Pipeline
from shell.ast import PositionalArg
from shell.ast import Program
from shell.ast import RecordExpr
from shell.ast import RecordField
from shell.ast import StringLiteral
from shell.ast import validate_program

from .model import Dependency
from .model import ExecutionPlan
from .model import PlanArgument
from .model import PlanValue
from .model import Step


def build_execution_plan(program: Program) -> ExecutionPlan:
    validate_program(program)

    steps: list[Step] = []
    dependencies: list[Dependency] = []
    previous_terminal_step_id: str | None = None
    step_counter = 0

    for statement_index, statement in enumerate(program.statements):
        if isinstance(statement, Binding):
            step = make_binding_step(statement, statement_index, step_counter)
            steps.append(step)
            if previous_terminal_step_id is not None:
                dependencies.append(make_program_order_dependency(previous_terminal_step_id, step.step_id))
            previous_terminal_step_id = step.step_id
            step_counter += 1
            continue

        if isinstance(statement, Pipeline):
            pipeline_steps, pipeline_dependencies = make_pipeline_steps(statement, statement_index, step_counter)
            if previous_terminal_step_id is not None:
                dependencies.append(make_program_order_dependency(previous_terminal_step_id, pipeline_steps[0].step_id))
            steps.extend(pipeline_steps)
            dependencies.extend(pipeline_dependencies)
            previous_terminal_step_id = pipeline_steps[-1].step_id
            step_counter += len(pipeline_steps)
            continue

        command_step = make_command_step(statement, statement_index, None, step_counter)
        steps.append(command_step)
        if previous_terminal_step_id is not None:
            dependencies.append(make_program_order_dependency(previous_terminal_step_id, command_step.step_id))
        previous_terminal_step_id = command_step.step_id
        step_counter += 1

    return ExecutionPlan(
        steps=tuple(steps),
        dependencies=tuple(dependencies),
    )


def make_binding_step(binding: Binding, statement_index: int, step_counter: int) -> Step:
    return Step(
        step_id=make_step_id(step_counter),
        kind="binding",
        statement_index=statement_index,
        pipeline_index=None,
        binding_name=binding.name.text,
        target=None,
        method=None,
        value=build_plan_value(binding.value),
        arguments=(),
    )


def make_pipeline_steps(
    pipeline: Pipeline,
    statement_index: int,
    step_counter: int,
) -> tuple[tuple[Step, ...], tuple[Dependency, ...]]:
    steps: list[Step] = []
    dependencies: list[Dependency] = []

    for pipeline_index, stage in enumerate(pipeline.stages):
        step = make_command_step(stage, statement_index, pipeline_index, step_counter + pipeline_index)
        steps.append(step)
        if pipeline_index > 0:
            dependencies.append(Dependency(
                kind="pipeline_stage_order",
                from_step_id=steps[pipeline_index - 1].step_id,
                to_step_id=step.step_id,
            ))

    return tuple(steps), tuple(dependencies)


def make_command_step(
    command: Invocation | InvokeForm,
    statement_index: int,
    pipeline_index: int | None,
    step_counter: int,
) -> Step:
    return Step(
        step_id=make_step_id(step_counter),
        kind="invoke_form" if isinstance(command, InvokeForm) else "invocation",
        statement_index=statement_index,
        pipeline_index=pipeline_index,
        binding_name=None,
        target=command.target.text,
        method=command.method.text,
        value=None,
        arguments=tuple(
            build_plan_argument(argument, position)
            for position, argument in enumerate(command.args)
        ),
    )


def build_plan_argument(argument: NamedArg | PositionalArg, position: int) -> PlanArgument:
    if isinstance(argument, NamedArg):
        return PlanArgument(
            position=position,
            kind="named",
            name=argument.name.text,
            value=build_plan_value(argument.value),
        )
    return PlanArgument(
        position=position,
        kind="positional",
        name=None,
        value=build_plan_value(argument.value),
    )


def build_plan_value(value: object) -> PlanValue:
    if isinstance(value, StringLiteral):
        return PlanValue(kind="string_literal", payload=value.value)
    if isinstance(value, IntLiteral):
        return PlanValue(kind="int_literal", payload=value.value)
    if isinstance(value, BoolLiteral):
        return PlanValue(kind="bool_literal", payload=value.value)
    if isinstance(value, NullLiteral):
        return PlanValue(kind="null_literal", payload=None)
    if isinstance(value, IdentifierExpr):
        return PlanValue(kind="identifier", payload=value.name.text)
    if isinstance(value, Invocation):
        return PlanValue(kind="invocation", payload=make_command_step(value, -1, None, -1))
    if isinstance(value, InvokeForm):
        return PlanValue(kind="invoke_form", payload=make_command_step(value, -1, None, -1))
    if isinstance(value, ListExpr):
        return PlanValue(
            kind="list_expr",
            payload=tuple(build_plan_value(element) for element in value.elements),
        )
    if isinstance(value, RecordExpr):
        return PlanValue(
            kind="record_expr",
            payload=tuple(build_record_field_value(field) for field in value.fields),
        )
    raise TypeError(f"unsupported plan value {type(value).__name__}")


def build_record_field_value(field: RecordField) -> tuple[str, PlanValue]:
    return field.name.text, build_plan_value(field.value)


def make_program_order_dependency(from_step_id: str, to_step_id: str) -> Dependency:
    return Dependency(
        kind="program_statement_order",
        from_step_id=from_step_id,
        to_step_id=to_step_id,
    )


def make_step_id(step_counter: int) -> str:
    return f"step-{step_counter}"
