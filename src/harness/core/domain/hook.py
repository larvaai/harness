from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .lifecycle import HookPoint
from .state import RuntimeState


@dataclass(slots=True)
class HookContext:
    run_id: str
    point: HookPoint
    state: RuntimeState
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class HookResult:
    hook_name: str
    point: HookPoint
    success: bool = True
    skipped: bool = False
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
