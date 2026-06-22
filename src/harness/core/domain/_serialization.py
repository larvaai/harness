from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any


def to_plain_data(value: Any) -> Any:
    """Convert core domain values into JSON-friendly primitive structures."""

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, datetime):
        return value.isoformat()

    if is_dataclass(value):
        return to_plain_data(asdict(value))

    if isinstance(value, dict):
        return {str(key): to_plain_data(item) for key, item in value.items()}

    if isinstance(value, list | tuple):
        return [to_plain_data(item) for item in value]

    return value
