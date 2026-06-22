from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from .domain import CodeFile, CodeReference


class CodeIndexError(ValueError):
    pass


class FilesystemCodeIndexer:
    def __init__(self, *, root: str | Path) -> None:
        self._root = Path(root).resolve()

    def list_files(self) -> list[CodeFile]:
        files: list[CodeFile] = []
        for path in self._iter_indexable_files():
            text = self._read_text(path)
            rel = self._relative_path(path)
            files.append(
                CodeFile(
                    path=rel,
                    language=_language_for_path(path),
                    size_bytes=path.stat().st_size,
                    line_count=_line_count(text) if text is not None else 0,
                    sha256=_sha256(path),
                )
            )
        return files

    def search_text(
        self,
        query: str,
        *,
        max_results: int = 50,
    ) -> list[CodeReference]:
        normalized_query = query.strip()
        if not normalized_query:
            raise CodeIndexError("query must not be empty")
        if max_results < 1:
            raise CodeIndexError("max_results must be greater than 0")

        needle = normalized_query.lower()
        references: list[CodeReference] = []
        for path in self._iter_indexable_files():
            text = self._read_text(path)
            if text is None:
                continue

            for line_number, line in enumerate(text.splitlines(), start=1):
                column = line.lower().find(needle)
                if column < 0:
                    continue

                references.append(
                    CodeReference(
                        query=normalized_query,
                        file=self._relative_path(path),
                        line=line_number,
                        column=column + 1,
                        context=line.rstrip(),
                        score=_score_match(path, line, needle),
                    )
                )

        ranked = sorted(references, key=lambda item: (-item.score, item.file, item.line))
        return ranked[:max_results]

    def read_file(
        self,
        path: str,
        *,
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> str:
        resolved = self._resolve_workspace_path(path)
        if not resolved.is_file():
            raise CodeIndexError(f"file not found: {path}")
        if not self._is_indexable_file(resolved):
            raise CodeIndexError(f"file is not indexable: {path}")

        text = self._read_text(resolved)
        if text is None:
            raise CodeIndexError(f"file is not valid utf-8 text: {path}")

        lines = text.splitlines()
        start = 1 if start_line is None else start_line
        end = len(lines) if end_line is None else end_line
        if start < 1:
            raise CodeIndexError("start_line must be greater than 0")
        if end < start:
            raise CodeIndexError("end_line must be greater than or equal to start_line")

        selected = lines[start - 1 : end]
        return "\n".join(
            f"{line_number}: {line}"
            for line_number, line in enumerate(selected, start=start)
        )

    def _iter_indexable_files(self) -> list[Path]:
        paths = self._git_visible_files()
        if not paths:
            paths = [path for path in self._root.rglob("*") if path.is_file()]

        files = [path for path in paths if self._is_indexable_file(path)]
        files.sort(key=self._relative_path)
        return files

    def _git_visible_files(self) -> list[Path]:
        try:
            result = subprocess.run(
                [
                    "git",
                    "ls-files",
                    "-z",
                    "--cached",
                    "--others",
                    "--exclude-standard",
                    "--",
                    ".",
                ],
                cwd=self._root,
                check=False,
                capture_output=True,
                text=False,
            )
        except OSError:
            return []
        if result.returncode != 0 or not result.stdout:
            return []

        paths: list[Path] = []
        for raw_path in result.stdout.split(b"\0"):
            if not raw_path:
                continue
            path = (self._root / raw_path.decode("utf-8")).resolve()
            if path.is_file():
                paths.append(path)
        return paths

    def _is_indexable_file(self, path: Path) -> bool:
        if not _is_relative_to(path.resolve(), self._root):
            return False
        rel_parts = path.relative_to(self._root).parts
        if any(part in _IGNORED_DIRS for part in rel_parts):
            return False
        if path.suffix.lower() in _IGNORED_SUFFIXES:
            return False
        return self._read_text(path) is not None

    def _resolve_workspace_path(self, path: str) -> Path:
        candidate = (self._root / path).resolve()
        if not _is_relative_to(candidate, self._root):
            raise CodeIndexError(f"path escapes workspace root: {path}")
        return candidate

    def _relative_path(self, path: Path) -> str:
        return path.relative_to(self._root).as_posix()

    def _read_text(self, path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return None
        except OSError:
            return None


_IGNORED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    "var",
}

_IGNORED_SUFFIXES = {
    ".db",
    ".gif",
    ".jpeg",
    ".jpg",
    ".pdf",
    ".png",
    ".pyc",
    ".sqlite",
}

_LANGUAGE_BY_SUFFIX = {
    ".md": "markdown",
    ".py": "python",
    ".toml": "toml",
    ".txt": "text",
    ".yaml": "yaml",
    ".yml": "yaml",
}


def _language_for_path(path: Path) -> str:
    return _LANGUAGE_BY_SUFFIX.get(path.suffix.lower(), "text")


def _line_count(text: str | None) -> int:
    if text is None:
        return 0
    if not text:
        return 0
    return len(text.splitlines())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _score_match(path: Path, line: str, needle: str) -> int:
    rel = path.as_posix().lower()
    lower_line = line.lower()
    score = lower_line.count(needle)
    if needle in rel:
        score += 5
    if lower_line.strip().startswith(("class ", "def ", "async def ")):
        score += 3
    return score


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
