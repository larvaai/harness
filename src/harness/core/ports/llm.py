from __future__ import annotations

from typing import Protocol

from harness.core.domain import LLMResponse, Message, ToolDefinition


class LLMPort(Protocol):
    async def complete(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
    ) -> LLMResponse:
        ...
