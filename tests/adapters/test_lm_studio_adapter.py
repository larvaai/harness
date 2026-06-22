from __future__ import annotations

import asyncio

from harness.adapters.llm import LMStudioConfig, LMStudioLLMAdapter
from harness.core.domain import Message, MessageRole, ToolDefinition


class FakeLMStudioAdapter(LMStudioLLMAdapter):
    def __init__(self, response: dict) -> None:
        super().__init__(LMStudioConfig(model="test-model"))
        self.response = response
        self.payloads: list[dict] = []

    def _post_json(self, path: str, payload: dict) -> dict:
        self.payloads.append({"path": path, "payload": payload})
        return self.response

    def _get_json(self, path: str) -> dict:
        return {
            "object": "list",
            "data": [
                {"id": "test-model", "object": "model"},
                {"id": "text-embedding-test", "object": "model"},
            ],
        }


def test_complete_maps_plain_content_to_final_answer() -> None:
    async def scenario() -> None:
        adapter = FakeLMStudioAdapter(
            {
                "model": "test-model",
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "harness-ok"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            }
        )

        response = await adapter.complete(
            [Message(role=MessageRole.USER, content="hello")]
        )

        assert response.content == "harness-ok"
        assert response.final_answer == "harness-ok"
        assert response.tool_calls == []
        assert adapter.payloads[0]["path"] == "/chat/completions"
        assert adapter.payloads[0]["payload"]["model"] == "test-model"

    asyncio.run(scenario())


def test_complete_maps_tool_calls_and_tool_specs() -> None:
    async def scenario() -> None:
        adapter = FakeLMStudioAdapter(
            {
                "model": "test-model",
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {
                                        "name": "read_file",
                                        "arguments": '{"path": "README.md"}',
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
            }
        )
        tool = ToolDefinition(
            name="read_file",
            description="Read a file",
            input_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        )

        response = await adapter.complete(
            [Message(role=MessageRole.USER, content="read")],
            tools=[tool],
        )

        assert response.final_answer is None
        assert response.tool_calls[0].id == "call_1"
        assert response.tool_calls[0].tool_name == "read_file"
        assert response.tool_calls[0].arguments == {"path": "README.md"}
        assert adapter.payloads[0]["payload"]["tools"][0]["function"]["name"] == "read_file"

    asyncio.run(scenario())


def test_list_models_returns_ids() -> None:
    async def scenario() -> None:
        adapter = FakeLMStudioAdapter({"choices": []})

        assert await adapter.list_models() == ["test-model", "text-embedding-test"]

    asyncio.run(scenario())
