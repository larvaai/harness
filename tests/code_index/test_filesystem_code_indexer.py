from __future__ import annotations

import shutil
import subprocess

import pytest

from harness.features.code_index import (
    CodeIndexError,
    FilesystemCodeIndexer,
)


def test_filesystem_code_indexer_lists_searches_and_reads_text_files(tmp_path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "memory.py").write_text(
        "class MemoryPort:\n"
        "    def save(self, state):\n"
        "        pass\n",
        encoding="utf-8",
    )
    (tmp_path / ".pytest_cache").mkdir()
    (tmp_path / ".pytest_cache" / "ignored.txt").write_text(
        "MemoryPort",
        encoding="utf-8",
    )

    indexer = FilesystemCodeIndexer(root=tmp_path)

    files = indexer.list_files()
    assert [file.path for file in files] == ["src/memory.py"]
    assert files[0].language == "python"
    assert files[0].line_count == 3

    matches = indexer.search_text("MemoryPort")
    assert len(matches) == 1
    assert matches[0].file == "src/memory.py"
    assert matches[0].line == 1

    chunk = indexer.read_file("src/memory.py", start_line=1, end_line=2)
    assert chunk == "1: class MemoryPort:\n2:     def save(self, state):"


def test_filesystem_code_indexer_rejects_paths_outside_workspace(tmp_path) -> None:
    indexer = FilesystemCodeIndexer(root=tmp_path)

    with pytest.raises(CodeIndexError, match="escapes workspace"):
        indexer.read_file("../secret.txt")


def test_filesystem_code_indexer_ranks_symbol_like_lines_before_docs(tmp_path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "docs" / "notes.md").write_text(
        "WorkspaceContextRetriever is mentioned here first.\n",
        encoding="utf-8",
    )
    (tmp_path / "src" / "context.py").write_text(
        "class WorkspaceContextRetriever:\n"
        "    pass\n",
        encoding="utf-8",
    )
    indexer = FilesystemCodeIndexer(root=tmp_path)

    matches = indexer.search_text("WorkspaceContextRetriever", max_results=1)

    assert matches[0].file == "src/context.py"


def test_filesystem_code_indexer_includes_untracked_git_files(tmp_path) -> None:
    if shutil.which("git") is None:
        pytest.skip("git is not installed")

    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "new_file.py").write_text("class NewFile:\n    pass\n", encoding="utf-8")
    indexer = FilesystemCodeIndexer(root=tmp_path)

    assert [file.path for file in indexer.list_files()] == ["new_file.py"]
