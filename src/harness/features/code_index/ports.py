from __future__ import annotations

from typing import Protocol

from .domain import CodeFile, CodeReference


class CodeIndexPort(Protocol):
    def list_files(self) -> list[CodeFile]:
        ...

    def search_text(
        self,
        query: str,
        *,
        max_results: int = 50,
    ) -> list[CodeReference]:
        ...

    def read_file(
        self,
        path: str,
        *,
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> str:
        ...
