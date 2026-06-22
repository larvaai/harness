from __future__ import annotations

from harness.features.code_index import (
    CODE_INDEX_READ_FILE_TOOL,
    CODE_INDEX_SEARCH_TEXT_TOOL,
    CodeIndexMCPServer,
)


def test_mcp_server_exposes_level_1_tools(tmp_path) -> None:
    (tmp_path / "app.py").write_text(
        "def run_task():\n"
        "    return 'ok'\n",
        encoding="utf-8",
    )
    server = CodeIndexMCPServer.for_workspace(workspace_root=tmp_path)

    initialize = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "0"},
            },
        }
    )
    assert initialize is not None
    assert initialize["result"]["capabilities"] == {"tools": {"listChanged": False}}

    tools = server.handle_message(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
    )
    assert tools is not None
    assert [tool["name"] for tool in tools["result"]["tools"]] == [
        "code_index.list_files",
        "code_index.search_text",
        "code_index.read_file",
    ]


def test_mcp_server_calls_search_and_read_tools(tmp_path) -> None:
    (tmp_path / "app.py").write_text(
        "def run_task():\n"
        "    return 'ok'\n",
        encoding="utf-8",
    )
    server = CodeIndexMCPServer.for_workspace(workspace_root=tmp_path)

    search_response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": CODE_INDEX_SEARCH_TEXT_TOOL,
                "arguments": {"query": "run_task"},
            },
        }
    )
    assert search_response is not None
    search_result = search_response["result"]["structuredContent"]
    assert search_result["count"] == 1
    assert search_result["matches"][0]["file"] == "app.py"

    read_response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": CODE_INDEX_READ_FILE_TOOL,
                "arguments": {"path": "app.py", "start_line": 1, "end_line": 1},
            },
        }
    )
    assert read_response is not None
    read_result = read_response["result"]["structuredContent"]
    assert read_result["content"] == "1: def run_task():"


def test_mcp_server_runs_code_index_hook_before_reading_file(tmp_path) -> None:
    (tmp_path / "app.py").write_text("print('ok')\n", encoding="utf-8")
    server = CodeIndexMCPServer.for_workspace(workspace_root=tmp_path)

    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": CODE_INDEX_READ_FILE_TOOL,
                "arguments": {"path": "../outside.py"},
            },
        }
    )

    assert response is not None
    assert response["result"]["isError"] is True
    assert "escapes workspace root" in response["result"]["content"][0]["text"]
