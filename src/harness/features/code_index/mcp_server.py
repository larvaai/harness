from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

from harness.adapters.checkpoint import InMemoryCheckpointStore
from harness.adapters.events import InMemoryEventPublisher
from harness.core.domain import RuntimeState, Task, ToolCall, ToolDefinition
from harness.core.services import LifecycleManager
from harness.core.use_cases import ExecuteToolCallUseCase

from .filesystem_indexer import FilesystemCodeIndexer
from .hooks import CodeIndexToolHookRunner
from .tools import CodeIndexToolExecutor, code_index_tool_definitions


PROTOCOL_VERSION = "2025-06-18"


@dataclass(frozen=True, slots=True)
class MCPError(Exception):
    code: int
    message: str
    data: Any | None = None


class CodeIndexMCPServer:
    def __init__(
        self,
        *,
        execute_tool_call: ExecuteToolCallUseCase,
        tools: list[ToolDefinition],
        protocol_version: str = PROTOCOL_VERSION,
    ) -> None:
        self._execute_tool_call = execute_tool_call
        self._tools = tools
        self._protocol_version = protocol_version

    @classmethod
    def for_workspace(cls, *, workspace_root: str | Path) -> CodeIndexMCPServer:
        code_index = FilesystemCodeIndexer(root=workspace_root)
        lifecycle = LifecycleManager(
            hook_runner=CodeIndexToolHookRunner(workspace_root=workspace_root),
            event_publisher=InMemoryEventPublisher(),
            checkpoint_store=InMemoryCheckpointStore(),
        )
        return cls(
            execute_tool_call=ExecuteToolCallUseCase(
                tool_executor=CodeIndexToolExecutor(code_index=code_index),
                lifecycle=lifecycle,
            ),
            tools=code_index_tool_definitions(),
        )

    def run_stdio(
        self,
        *,
        input_stream: TextIO | None = None,
        output_stream: TextIO | None = None,
    ) -> None:
        input_stream = input_stream or sys.stdin
        output_stream = output_stream or sys.stdout

        for line in input_stream:
            if not line.strip():
                continue
            response = self.handle_line(line)
            if response is None:
                continue
            output_stream.write(json.dumps(response, ensure_ascii=False) + "\n")
            output_stream.flush()

    def handle_line(self, line: str) -> dict[str, Any] | None:
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            return _error_response(None, -32700, f"Parse error: {exc.msg}")
        return self.handle_message(message)

    def handle_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        if not isinstance(message, dict):
            return _error_response(None, -32600, "Invalid request")

        request_id = message.get("id")
        method = message.get("method")
        if not isinstance(method, str):
            return _error_response(request_id, -32600, "Missing method")

        is_notification = "id" not in message
        try:
            result = self._dispatch(method, _object_params(message.get("params")))
        except MCPError as exc:
            if is_notification:
                return None
            return _error_response(request_id, exc.code, exc.message, exc.data)
        except Exception as exc:
            if is_notification:
                return None
            return _error_response(request_id, -32603, str(exc))

        if is_notification:
            return None
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def _dispatch(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method == "initialize":
            return self._initialize(params)
        if method in {"notifications/initialized", "notifications/cancelled"}:
            return {}
        if method == "ping":
            return {}
        if method == "tools/list":
            return {"tools": [_mcp_tool_definition(tool) for tool in self._tools]}
        if method == "tools/call":
            return self._call_tool(params)
        raise MCPError(-32601, f"Method not found: {method}")

    def _initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        requested_version = params.get("protocolVersion")
        protocol_version = (
            requested_version
            if isinstance(requested_version, str)
            else self._protocol_version
        )
        return {
            "protocolVersion": protocol_version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {
                "name": "harness-code-index",
                "title": "Harness Code Index",
                "version": "0.1.0",
            },
            "instructions": (
                "Read-only code_index feature tools for listing workspace files, "
                "searching text, and reading line-bounded file chunks."
            ),
        }

    def _call_tool(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(name, str):
            raise MCPError(-32602, "Tool name must be a string")
        if not isinstance(arguments, dict):
            raise MCPError(-32602, "Tool arguments must be an object")

        if name not in {tool.name for tool in self._tools}:
            raise MCPError(-32602, f"Unknown tool: {name}")

        state = RuntimeState.new(
            Task(f"MCP request for {name}"),
            run_id="mcp_code_index_request",
        )
        tool_call = ToolCall(
            tool_name=name,
            arguments=arguments,
            requested_by="mcp",
            metadata={"feature": "code_index"},
        )
        try:
            result = asyncio.run(
                self._execute_tool_call.execute(state=state, tool_call=tool_call)
            )
        except PermissionError as exc:
            return _tool_error(str(exc))

        if not result.success:
            return _tool_error(result.error or "Code index tool failed")

        structured_content = result.metadata.get("structured_content")
        if not isinstance(structured_content, dict):
            structured_content = {"output": result.output or ""}
        return _tool_result(structured_content)


def _mcp_tool_definition(tool: ToolDefinition) -> dict[str, Any]:
    return {
        "name": tool.name,
        "title": tool.name.replace("code_index.", "Code index "),
        "description": tool.description,
        "inputSchema": tool.input_schema,
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    }


def _tool_result(structured_content: dict[str, Any]) -> dict[str, Any]:
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(structured_content, indent=2, ensure_ascii=False),
            }
        ],
        "structuredContent": structured_content,
        "isError": False,
    }


def _tool_error(message: str) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": message}],
        "isError": True,
    }


def _object_params(params: Any) -> dict[str, Any]:
    if params is None:
        return {}
    if not isinstance(params, dict):
        raise MCPError(-32602, "params must be an object")
    return params


def _error_response(
    request_id: Any,
    code: int,
    message: str,
    data: Any | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}
