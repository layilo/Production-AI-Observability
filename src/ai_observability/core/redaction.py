from __future__ import annotations

from typing import Any

REDACTED = "[REDACTED]"


def redact_value(value: Any, sensitive_keys: set[str]) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if key.lower() in sensitive_keys:
                redacted[key] = REDACTED
            else:
                redacted[key] = redact_value(item, sensitive_keys)
        return redacted
    if isinstance(value, list):
        return [redact_value(item, sensitive_keys) for item in value]
    return value

