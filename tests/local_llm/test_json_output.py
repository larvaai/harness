from __future__ import annotations

import pytest

from harness.core.services import JsonOutputError, parse_json_object


def test_parse_json_object_from_plain_json() -> None:
    assert parse_json_object('{"ok": true}') == {"ok": True}


def test_parse_json_object_from_markdown_fence() -> None:
    assert parse_json_object('```json\n{"ok": true}\n```') == {"ok": True}


def test_parse_json_object_from_surrounding_text() -> None:
    assert parse_json_object('Here is JSON:\n{"ok": true}\nDone.') == {"ok": True}


def test_parse_json_object_rejects_non_json() -> None:
    with pytest.raises(JsonOutputError):
        parse_json_object("not json")
