import json

import pytest

from agents.common.response_parser import A2AInvocationError, parse_a2a_response


def test_extracts_task_artifacts_in_order() -> None:
    payload = {
        "jsonrpc": "2.0",
        "id": "1",
        "result": {
            "artifacts": [
                {"parts": [{"kind": "text", "text": "first"}]},
                {"parts": [{"kind": "text", "text": "second"}]},
            ]
        },
    }

    assert parse_a2a_response(json.dumps(payload).encode()) == "first\nsecond"


def test_extracts_direct_message_result() -> None:
    payload = {
        "jsonrpc": "2.0",
        "id": "1",
        "result": {"role": "agent", "parts": [{"kind": "text", "text": "answer"}]},
    }

    assert parse_a2a_response(json.dumps(payload)) == "answer"


@pytest.mark.parametrize("payload", [b"not-json", b"[]", b'{"result": {}}'])
def test_rejects_invalid_or_empty_responses(payload: bytes) -> None:
    with pytest.raises(A2AInvocationError):
        parse_a2a_response(payload)


def test_marks_session_conflict_retryable() -> None:
    payload = {
        "jsonrpc": "2.0",
        "id": "1",
        "error": {"code": -32054, "message": "Session operation in progress"},
    }

    with pytest.raises(A2AInvocationError) as captured:
        parse_a2a_response(json.dumps(payload))

    assert captured.value.json_rpc_code == -32054
    assert captured.value.retryable is True


def test_ordinary_json_rpc_error_is_not_retryable() -> None:
    payload = {
        "jsonrpc": "2.0",
        "id": "1",
        "error": {"code": -32602, "message": "Invalid params"},
    }

    with pytest.raises(A2AInvocationError) as captured:
        parse_a2a_response(json.dumps(payload))

    assert captured.value.retryable is False

