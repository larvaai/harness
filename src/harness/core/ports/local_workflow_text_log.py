from __future__ import annotations

from typing import Any, Protocol

from harness.core.domain import ContextPack, LocalWorkflowResult


class LocalWorkflowTextLogPort(Protocol):
    async def start_run(self, *, run_id: str, user_request: str) -> None:
        ...

    async def log_context_pack(self, *, context_pack: ContextPack) -> None:
        ...

    async def log_llm_step(
        self,
        *,
        step_name: str,
        system_prompt: str,
        user_payload: str,
        raw_text: str,
        parsed_json: dict[str, Any],
    ) -> None:
        ...

    async def finish_run(self, *, result: LocalWorkflowResult) -> None:
        ...
