from __future__ import annotations

from typing import Protocol

from harness.core.domain import ContextPack, TaskGraph, TaskSpec


class ContextRetrieverPort(Protocol):
    async def retrieve(self, task_spec: TaskSpec, task_graph: TaskGraph) -> ContextPack:
        ...
