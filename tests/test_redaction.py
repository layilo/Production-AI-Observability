from ai_observability.core.redaction import REDACTED, redact_value


def test_redact_value_masks_sensitive_keys_recursively() -> None:
    payload = {
        "prompt": "secret prompt",
        "nested": {"authorization": "Bearer abc", "safe": "ok"},
        "items": [{"api_key": "xyz"}, {"value": "keep"}],
    }
    result = redact_value(payload, {"prompt", "authorization", "api_key"})
    assert result["prompt"] == REDACTED
    assert result["nested"]["authorization"] == REDACTED
    assert result["nested"]["safe"] == "ok"
    assert result["items"][0]["api_key"] == REDACTED

