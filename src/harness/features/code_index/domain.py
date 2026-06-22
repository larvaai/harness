from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from harness.core.domain._serialization import to_plain_data


@dataclass(frozen=True, slots=True)
class CodeFile:
    path: str
    language: str
    size_bytes: int
    line_count: int
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(self)


@dataclass(frozen=True, slots=True)
class CodeReference:
    query: str
    file: str
    line: int
    column: int | None
    context: str
    score: int = 1

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(self)
