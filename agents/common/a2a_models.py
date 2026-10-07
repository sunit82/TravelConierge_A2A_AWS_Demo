from __future__ import annotations

import uuid
from typing import TypedDict


class TextPart(TypedDict):
    kind: str
    text: str


class A2AMessage(TypedDict):
    role: str
    parts: list[TextPart]
    messageId: str


class MessageSendParams(TypedDict):
    message: A2AMessage


class JsonRpcRequest(TypedDict):
    jsonrpc: str
    id: str
    method: str
    params: MessageSendParams


def build_message_send_request(text: str) -> JsonRpcRequest:
    normalized = text.strip()
    if not normalized:
        raise ValueError("A2A message text must not be blank")
    return {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": normalized}],
                "messageId": str(uuid.uuid4()),
            }
        },
    }

