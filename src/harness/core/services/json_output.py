from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from harness.core.domain import LLMResponse, Message, MessageRole
from harness.core.ports import LLMPort


class JsonOutputError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class JsonWorkerResponse:
    data: dict[str, Any]
    raw_text: str
    llm_response: LLMResponse


class LocalLLMJsonWorker:
    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    async def run_json(
        self,
        *,
        system_prompt: str,
        user_payload: str,
    ) -> JsonWorkerResponse:
        response = await self._llm.complete(
            [
                Message(role=MessageRole.SYSTEM, content=system_prompt),
                Message(role=MessageRole.USER, content=user_payload),
            ]
        )
        raw_text = self._response_text(response)
        return JsonWorkerResponse(
            data=parse_json_object(raw_text),
            raw_text=raw_text,
            llm_response=response,
        )

    def _response_text(self, response: LLMResponse) -> str:
        content = (response.content or "").strip()
        if content:
            return content

        reasoning_content = response.metadata.get("reasoning_content")
        if isinstance(reasoning_content, str) and reasoning_content.strip():
            return reasoning_content.strip()

        raise JsonOutputError("LLM returned empty content.")


def parse_json_object(text: str) -> dict[str, Any]:
    candidates = _json_candidates(text)
    errors: list[str] = []
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError as exc:
            errors.append(str(exc))
            continue

        if isinstance(parsed, dict):
            return parsed

        errors.append("Parsed JSON is not an object.")

    raise JsonOutputError(
        "Could not parse a JSON object from LLM output. "
        f"Errors: {'; '.join(errors) or 'no JSON candidates found'}"
    )


def _json_candidates(text: str) -> list[str]:
    stripped = text.strip()
    candidates = [stripped]

    fenced = re.findall(r"```(?:json)?\s*(.*?)```", stripped, flags=re.DOTALL)
    candidates.extend(item.strip() for item in fenced)

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        candidates.append(stripped[start : end + 1])

    unique: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in unique:
            unique.append(candidate)
    return unique
