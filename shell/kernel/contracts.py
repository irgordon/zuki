from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class KernelErrorKind(str, Enum):
    SPAWN = "spawn"
    SEND = "send"
    RECEIVE = "receive"
    SHUTDOWN = "shutdown"


@dataclass(frozen=True)
class KernelError:
    kind: KernelErrorKind
    code: str
    detail: str


@dataclass(frozen=True)
class SpawnRequest:
    plan_id: str
    capability_handles: tuple[str, ...]


@dataclass(frozen=True)
class SpawnResult:
    accepted: bool
    handle_id: str | None
    error: KernelError | None


@dataclass(frozen=True)
class SendRequest:
    handle_id: str
    payload: object


@dataclass(frozen=True)
class SendResult:
    accepted: bool
    sequence_id: int | None
    error: KernelError | None


@dataclass(frozen=True)
class ReceiveRequest:
    handle_id: str
    max_items: int


@dataclass(frozen=True)
class ReceiveResult:
    messages: tuple[object, ...]
    error: KernelError | None


@dataclass(frozen=True)
class ShutdownRequest:
    handle_id: str


@dataclass(frozen=True)
class ShutdownResult:
    accepted: bool
    error: KernelError | None


class KernelRuntimeContract(Protocol):
    def spawn(self, request: SpawnRequest) -> SpawnResult:
        ...

    def send(self, request: SendRequest) -> SendResult:
        ...

    def receive(self, request: ReceiveRequest) -> ReceiveResult:
        ...

    def shutdown(self, request: ShutdownRequest) -> ShutdownResult:
        ...
