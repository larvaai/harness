from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol

from harness.core.domain import ContextItem, ContextPack, TaskGraph, TaskSpec
from harness.features.code_index import CodeFile, CodeReference


class ContextCodeIndex(Protocol):
    def list_files(self) -> list[CodeFile]:
        ...

    def search_text(
        self,
        query: str,
        *,
        max_results: int = 50,
    ) -> list[CodeReference]:
        ...


class WorkspaceContextRetriever:
    def __init__(
        self,
        *,
        root: str | Path,
        max_items: int = 8,
        chunk_radius: int = 35,
        token_budget: int = 3500,
        code_index: ContextCodeIndex | None = None,
    ) -> None:
        self._root = Path(root).resolve()
        self._max_items = max_items
        self._chunk_radius = chunk_radius
        self._token_budget = token_budget
        self._code_index = code_index

    async def retrieve(self, task_spec: TaskSpec, task_graph: TaskGraph) -> ContextPack:
        terms = _search_terms(task_spec, task_graph)
        path_hints = _path_hints(task_spec, task_graph, self._root)
        items: list[ContextItem] = [
            ContextItem(
                type="task_spec",
                content=(
                    f"goal: {task_spec.goal}\n"
                    f"task_type: {task_spec.task_type}\n"
                    f"constraints: {', '.join(task_spec.constraints)}"
                ),
            )
        ]

        for path, score in self._rank_files(terms, path_hints):
            if len(items) >= self._max_items:
                break
            item = self._chunk_for_file(path, terms, score)
            if item is not None:
                items.append(item)

        if len(items) == 1:
            items.append(self._file_tree_item())

        return ContextPack(
            purpose=f"Context for: {task_spec.goal}",
            token_budget=self._token_budget,
            items=items,
        )

    def _rank_files(
        self,
        terms: set[str],
        path_hints: list[str],
    ) -> list[tuple[Path, int]]:
        if self._code_index is not None:
            return self._rank_files_with_code_index(terms, path_hints)

        ranked: list[tuple[Path, int]] = []
        for path in self._iter_text_files():
            rel = path.relative_to(self._root).as_posix().lower()
            if path_hints and not any(
                rel == hint or rel.startswith(f"{hint}/") for hint in path_hints
            ):
                continue

            text = self._read_text(path)
            if text is None:
                continue

            searchable = f"{rel}\n{text.lower()}"
            score = 0
            if path_hints and any(
                rel == hint or rel.startswith(f"{hint}/") for hint in path_hints
            ):
                score += 100
            for term in terms:
                if term in rel:
                    score += 5
                score += searchable.count(term)

            if score > 0:
                ranked.append((path, score))

        ranked.sort(key=lambda item: (-item[1], item[0].as_posix()))
        return ranked

    def _rank_files_with_code_index(
        self,
        terms: set[str],
        path_hints: list[str],
    ) -> list[tuple[Path, int]]:
        scores: dict[str, int] = {}
        for term in terms:
            try:
                references = self._code_index.search_text(term, max_results=500)
            except ValueError:
                continue

            for reference in references:
                rel = reference.file.lower()
                if path_hints and not any(
                    rel == hint or rel.startswith(f"{hint}/") for hint in path_hints
                ):
                    continue
                scores[reference.file] = scores.get(reference.file, 0) + reference.score

        if path_hints:
            for file in self._code_index.list_files():
                rel = file.path.lower()
                if any(rel == hint or rel.startswith(f"{hint}/") for hint in path_hints):
                    scores[file.path] = scores.get(file.path, 0) + 100

        ranked = [
            (self._root / rel_path, score)
            for rel_path, score in scores.items()
            if score > 0 and (self._root / rel_path).is_file()
        ]
        ranked.sort(key=lambda item: (-item[1], item[0].as_posix()))
        return ranked

    def _chunk_for_file(
        self,
        path: Path,
        terms: set[str],
        score: int,
    ) -> ContextItem | None:
        text = self._read_text(path)
        if text is None:
            return None

        lines = text.splitlines()
        match_line = self._first_match_line(lines, terms)
        if match_line is None:
            match_line = 0

        start = max(0, match_line - self._chunk_radius)
        end = min(len(lines), match_line + self._chunk_radius + 1)
        rel = path.relative_to(self._root).as_posix()
        numbered = [
            f"{line_number}: {line}"
            for line_number, line in enumerate(lines[start:end], start=start + 1)
        ]

        return ContextItem(
            type="code_chunk",
            file=rel,
            start_line=start + 1,
            end_line=end,
            content=f"score: {score}\n" + "\n".join(numbered),
        )

    def _file_tree_item(self) -> ContextItem:
        if self._code_index is None:
            paths = [
                path.relative_to(self._root).as_posix()
                for path in self._iter_text_files()
            ][:80]
        else:
            paths = [file.path for file in self._code_index.list_files()][:80]
        return ContextItem(
            type="file_tree",
            content="\n".join(paths) if paths else "<empty workspace>",
        )

    def _iter_text_files(self) -> list[Path]:
        ignored_dirs = {
            ".git",
            ".mypy_cache",
            ".pytest_cache",
            "__pycache__",
            "node_modules",
            ".venv",
            "venv",
        }
        ignored_suffixes = {
            ".pyc",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".pdf",
            ".sqlite",
            ".db",
        }

        files: list[Path] = []
        for path in self._root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in ignored_dirs for part in path.parts):
                continue
            if path.suffix.lower() in ignored_suffixes:
                continue
            files.append(path)

        files.sort(key=lambda item: item.relative_to(self._root).as_posix())
        return files

    def _read_text(self, path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return None
        except OSError:
            return None

    def _first_match_line(self, lines: list[str], terms: set[str]) -> int | None:
        for index, line in enumerate(lines):
            lower = line.lower()
            if any(term in lower for term in terms):
                return index
        return None


def _workflow_text(task_spec: TaskSpec, task_graph: TaskGraph) -> str:
    return " ".join(
        [
            task_spec.goal,
            task_spec.task_type,
            " ".join(task_spec.success_criteria),
            " ".join(task_spec.constraints),
            " ".join(task_spec.unknowns),
            " ".join(task.name for task in task_graph.tasks),
            " ".join(task.expected_output for task in task_graph.tasks),
        ]
    )


def _search_terms(task_spec: TaskSpec, task_graph: TaskGraph) -> set[str]:
    text = _workflow_text(task_spec, task_graph)
    terms = {
        term.lower()
        for term in re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,}", text)
        if term.lower()
        not in {
            "this",
            "that",
            "with",
            "from",
            "have",
            "into",
            "only",
            "task",
            "tasks",
            "output",
            "string",
        }
    }

    # Keep core harness words available even if the normalizer paraphrases them.
    for keyword in ("harness", "local", "llm", "workflow", "hook", "checkpoint"):
        if keyword in text.lower():
            terms.add(keyword)
    return terms or {"harness"}


def _path_hints(
    task_spec: TaskSpec,
    task_graph: TaskGraph,
    root: Path,
) -> list[str]:
    text = _workflow_text(task_spec, task_graph)
    hints: list[str] = []
    for candidate in re.findall(r"[A-Za-z0-9_./-]+/[A-Za-z0-9_./-]+", text):
        normalized = candidate.strip("./").rstrip("/").lower()
        if not normalized:
            continue
        if (root / normalized).exists() and normalized not in hints:
            hints.append(normalized)
    return hints
