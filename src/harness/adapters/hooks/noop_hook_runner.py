from __future__ import annotations

from harness.core.domain import HookContext, HookPoint, HookResult


class NoopHookRunner:
    async def run(self, point: HookPoint, context: HookContext) -> list[HookResult]:
        return [HookResult(hook_name="noop", point=point, skipped=True)]
