from __future__ import annotations

import json
from io import BytesIO
from typing import Any

import pytest

from agents.common.response_parser import A2AInvocationError
from agents.main_agent.subagent_client import SubagentClient, _read_payload


class FakeRuntimeClient:
    def __init__(self, payloads: list[dict[str, Any]]) -> None:
        self.payloads = payloads
        self.calls: list[dict[str, Any]] = []

    def invoke_agent_runtime(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        payload = self.payloads.pop(0)
        return {"payload": BytesIO(json.dumps(payload).encode())}


def successful_payload(text: str = "specialist answer") -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": "response",
        "result": {"parts": [{"kind": "text", "text": text}]},
    }


def test_reads_current_agentcore_response_field() -> None:
    content = json.dumps(successful_payload()).encode()

    assert _read_payload({"response": BytesIO(content)}) == content


def test_reads_legacy_payload_field() -> None:
    content = json.dumps(successful_payload()).encode()

    assert _read_payload({"payload": content}) == content


def test_invokes_configured_runtime_with_a2a_payload() -> None:
    runtime_arn = (
        "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/WeatherAgent-abc"
    )
    fake = FakeRuntimeClient([successful_payload()])

    answer = SubagentClient(runtime_arn, fake).ask("Tokyo weather")

    assert answer == "specialist answer"
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["agentRuntimeArn"] == runtime_arn
    assert call["contentType"] == "application/json"
    assert call["accept"] == "application/json"
    assert call["runtimeSessionId"]
    request = json.loads(call["payload"])
    assert request["method"] == "message/send"


def test_retries_only_retryable_a2a_conflict() -> None:
    conflict = {
        "jsonrpc": "2.0",
        "id": "response",
        "error": {"code": -32054, "message": "Session operation in progress"},
    }
    fake = FakeRuntimeClient([conflict, successful_payload("recovered")])
    sleeps: list[float] = []

    answer = SubagentClient(runtime_arn="runtime", client=fake, sleep=sleeps.append).ask(
        "request"
    )

    assert answer == "recovered"
    assert len(fake.calls) == 2
    assert len(sleeps) == 1


def test_does_not_retry_non_retryable_error() -> None:
    error = {
        "jsonrpc": "2.0",
        "id": "response",
        "error": {"code": -32602, "message": "Invalid params"},
    }
    fake = FakeRuntimeClient([error, successful_payload()])

    with pytest.raises(A2AInvocationError):
        SubagentClient(runtime_arn="runtime", client=fake, sleep=lambda _: None).ask("request")

    assert len(fake.calls) == 1

