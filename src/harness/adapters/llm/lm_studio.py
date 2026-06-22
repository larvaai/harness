from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from harness.core.domain import (
    LLMResponse,
    Message,
    MessageRole,
    ToolCall,
    ToolDefinition,
)


class LMStudioError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class LMStudioConfig:
    base_url: str = "http://localhost:1234/v1"
    model: str | None = None
    temperature: float = 0.2
    timeout_seconds: float = 120.0
    max_tokens: int | None = None


class LMStudioLLMAdapter:
    def __init__(self, config: LMStudioConfig | None = None) -> None:
        self._config = config or LMStudioConfig()
        self._resolved_model: str | None = self._config.model

    async def complete(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
    ) -> LLMResponse:
        return await asyncio.to_thread(self._complete_sync, messages, tools or [])

    async def list_models(self) -> list[str]:
        return await asyncio.to_thread(self._list_models_sync)

    def _complete_sync(
        self,
        messages: list[Message],
        tools: list[ToolDefinition],
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self._model(),
            "messages": [self._message_to_wire(message) for message in messages],
            "temperature": self._config.temperature,
            "stream": False,
        }

        if self._config.max_tokens is not None:
            payload["max_tokens"] = self._config.max_tokens

        if tools:
            payload["tools"] = [self._tool_to_wire(tool) for tool in tools]

        response = self._post_json("/chat/completions", payload)

        try:
            choice = response["choices"][0]
            message = choice["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LMStudioError(f"Unexpected LM Studio response shape: {response}") from exc

        content = message.get("content") or ""
        tool_calls = self._parse_tool_calls(message.get("tool_calls") or [])

        return LLMResponse(
            content=content,
            final_answer=content if content and not tool_calls else None,
            tool_calls=tool_calls,
            metadata={
                "model": response.get("model"),
                "finish_reason": choice.get("finish_reason"),
                "reasoning_content": message.get("reasoning_content"),
                "usage": response.get("usage"),
            },
        )

    def _model(self) -> str:
        if self._resolved_model:
            return self._resolved_model

        models = self._list_models_sync()
        for model in models:
            if "embedding" not in model.lower() and "embed" not in model.lower():
                self._resolved_model = model
                return model

        raise LMStudioError("LM Studio did not return a non-embedding model.")

    def _list_models_sync(self) -> list[str]:
        response = self._get_json("/models")
        data = response.get("data")
        if not isinstance(data, list):
            raise LMStudioError(f"Unexpected LM Studio models response: {response}")

        models = [item.get("id") for item in data if isinstance(item, dict)]
        return [model for model in models if isinstance(model, str) and model]

    def _message_to_wire(self, message: Message) -> dict[str, Any]:
        item: dict[str, Any] = {
            "role": message.role.value,
            "content": message.content,
        }

        if message.name:
            item["name"] = message.name

        if message.role == MessageRole.TOOL and message.tool_call_id:
            item["tool_call_id"] = message.tool_call_id

        return item

    def _tool_to_wire(self, tool: ToolDefinition) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema,
            },
        }

    def _parse_tool_calls(self, raw_tool_calls: list[Any]) -> list[ToolCall]:
        parsed: list[ToolCall] = []
        for raw_call in raw_tool_calls:
            if not isinstance(raw_call, dict):
                continue

            function = raw_call.get("function") or {}
            if not isinstance(function, dict):
                continue

            name = function.get("name")
            if not isinstance(name, str) or not name:
                continue

            raw_arguments = function.get("arguments") or {}
            arguments = self._parse_tool_arguments(raw_arguments)
            tool_call_id = raw_call.get("id")
            kwargs: dict[str, Any] = {
                "tool_name": name,
                "arguments": arguments,
                "requested_by": "lm_studio",
                "metadata": {"raw": raw_call},
            }
            if isinstance(tool_call_id, str) and tool_call_id:
                kwargs["id"] = tool_call_id

            parsed.append(ToolCall(**kwargs))

        return parsed

    def _parse_tool_arguments(self, raw_arguments: Any) -> dict[str, Any]:
        if isinstance(raw_arguments, dict):
            return raw_arguments

        if isinstance(raw_arguments, str):
            try:
                parsed = json.loads(raw_arguments)
            except json.JSONDecodeError:
                return {"_raw": raw_arguments}

            if isinstance(parsed, dict):
                return parsed

            return {"_value": parsed}

        return {"_value": raw_arguments}

    def _get_json(self, path: str) -> dict[str, Any]:
        request = Request(self._url(path), method="GET")
        return self._send(request)

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            self._url(path),
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return self._send(request)

    def _send(self, request: Request) -> dict[str, Any]:
        try:
            with urlopen(request, timeout=self._config.timeout_seconds) as response:
                raw_body = response.read().decode("utf-8")
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise LMStudioError(
                f"LM Studio HTTP {exc.code} for {request.full_url}: {body}"
            ) from exc
        except URLError as exc:
            raise LMStudioError(
                f"Could not reach LM Studio at {request.full_url}: {exc.reason}"
            ) from exc

        try:
            decoded = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise LMStudioError(f"LM Studio returned invalid JSON: {raw_body}") from exc

        if not isinstance(decoded, dict):
            raise LMStudioError(f"LM Studio returned non-object JSON: {decoded}")

        if "error" in decoded:
            raise LMStudioError(f"LM Studio returned error: {decoded['error']}")

        return decoded

    def _url(self, path: str) -> str:
        return f"{self._config.base_url.rstrip('/')}/{path.lstrip('/')}"
