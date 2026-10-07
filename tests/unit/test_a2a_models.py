from agents.common.a2a_models import build_message_send_request


def test_builds_message_send_request() -> None:
    request = build_message_send_request("  hello  ")

    assert request["jsonrpc"] == "2.0"
    assert request["method"] == "message/send"
    assert request["params"]["message"]["role"] == "user"
    assert request["params"]["message"]["parts"] == [{"kind": "text", "text": "hello"}]
    assert request["id"]
    assert request["params"]["message"]["messageId"]


def test_rejects_blank_request() -> None:
    try:
        build_message_send_request("   ")
    except ValueError as exc:
        assert "must not be blank" in str(exc)
    else:
        raise AssertionError("Expected blank request to fail")

