from __future__ import annotations

import json
from typing import Any


class A2AInvocationError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        json_rpc_code: int | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.json_rpc_code = json_rpc_code
        self.retryable = retryable


def _text_parts(parts: object) -> list[str]:
    if not isinstance(parts, list):
        return []
    texts: list[str] = []
    for part in parts:
        if (
            isinstance(part, dict)
            and part.get("kind") == "text"
            and isinstance(part.get("text"), str)
            and part["text"].strip()
        ):
            texts.append(part["text"].strip())
    return texts


def _extract_text(result: object) -> list[str]:
    if not isinstance(result, dict):
        return []

    texts = _text_parts(result.get("parts"))
    artifacts = result.get("artifacts")
    if isinstance(artifacts, list):
        for artifact in artifacts:
            if isinstance(artifact, dict):
                texts.extend(_text_parts(artifact.get("parts")))
    return texts


def parse_a2a_response(payload: bytes | str) -> str:
    try:
        decoded: Any = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as exc:
        raise A2AInvocationError("Agent returned malformed JSON") from exc

    if not isinstance(decoded, dict):
        raise A2AInvocationError("Agent response must be a JSON object")

    error = decoded.get("error")
    if isinstance(error, dict):
        code = error.get("code")
        parsed_code = code if isinstance(code, int) else None
        message = error.get("message")
        detail = message if isinstance(message, str) and message else "Unknown JSON-RPC error"
        retryable = parsed_code == -32054
        raise A2AInvocationError(
            f"Agent JSON-RPC error: {detail}",
            json_rpc_code=parsed_code,
            retryable=retryable,
        )

    texts = _extract_text(decoded.get("result"))
    if not texts:
        raise A2AInvocationError("Agent response did not contain any text output")
    return "\n".join(texts)

