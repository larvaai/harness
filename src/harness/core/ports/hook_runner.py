from __future__ import annotations

from typing import Protocol

from harness.core.domain import HookContext, HookPoint, HookResult


class HookRunnerPort(Protocol):
    async def run(self, point: HookPoint, context: HookContext) -> list[HookResult]:
        ...
