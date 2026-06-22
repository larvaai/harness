"""Code index feature package."""

from .domain import CodeFile, CodeReference
from .filesystem_indexer import CodeIndexError, FilesystemCodeIndexer
from .hooks import CodeIndexToolHookRunner
from .mcp_server import CodeIndexMCPServer
from .ports import CodeIndexPort
from .tools import (
    CODE_INDEX_LIST_FILES_TOOL,
    CODE_INDEX_READ_FILE_TOOL,
    CODE_INDEX_SEARCH_TEXT_TOOL,
    CodeIndexToolExecutor,
    code_index_tool_definitions,
)

__all__ = [
    "CODE_INDEX_LIST_FILES_TOOL",
    "CODE_INDEX_READ_FILE_TOOL",
    "CODE_INDEX_SEARCH_TEXT_TOOL",
    "CodeFile",
    "CodeIndexError",
    "CodeIndexMCPServer",
    "CodeIndexPort",
    "CodeIndexToolExecutor",
    "CodeIndexToolHookRunner",
    "CodeReference",
    "FilesystemCodeIndexer",
    "code_index_tool_definitions",
]
