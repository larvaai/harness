from __future__ import annotations

import asyncio

from harness.adapters.context import WorkspaceContextRetriever
from harness.core.domain import MicroTask, TaskGraph, TaskSpec
from harness.features.code_index import FilesystemCodeIndexer


def test_workspace_context_retriever_returns_matching_chunk(tmp_path) -> None:
    async def scenario() -> None:
        file_path = tmp_path / "memory.py"
        file_path.write_text(
            "class MemoryPort:\n"
            "    def save(self, state):\n"
            "        pass\n",
            encoding="utf-8",
        )
        retriever = WorkspaceContextRetriever(root=tmp_path)

        context = await retriever.retrieve(
            TaskSpec(
                goal="Find MemoryPort save behavior",
                task_type="read_only_analysis",
                success_criteria=["Find source"],
            ),
            TaskGraph(
                tasks=[
                    MicroTask(
                        id="T1",
                        name="Locate MemoryPort",
                        type="read_only",
                        expected_output="Relevant file",
                    )
                ]
            ),
        )

        assert any(item.file == "memory.py" for item in context.items)
        assert "MemoryPort" in "\n".join(item.content for item in context.items)

    asyncio.run(scenario())


def test_workspace_context_retriever_can_use_code_index(tmp_path) -> None:
    async def scenario() -> None:
        file_path = tmp_path / "indexed_context.py"
        file_path.write_text(
            "class IndexedContext:\n"
            "    pass\n",
            encoding="utf-8",
        )
        retriever = WorkspaceContextRetriever(
            root=tmp_path,
            code_index=FilesystemCodeIndexer(root=tmp_path),
        )

        context = await retriever.retrieve(
            TaskSpec(
                goal="Find IndexedContext",
                task_type="read_only_analysis",
                success_criteria=["Find source"],
            ),
            TaskGraph(
                tasks=[
                    MicroTask(
                        id="T1",
                        name="Locate IndexedContext",
                        type="read_only",
                        expected_output="Relevant file",
                    )
                ]
            ),
        )

        assert any(item.file == "indexed_context.py" for item in context.items)

    asyncio.run(scenario())
