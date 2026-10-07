from __future__ import annotations

import json
import logging
import random
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from agents.common.a2a_models import build_message_send_request
from agents.common.response_parser import A2AInvocationError, parse_a2a_response

LOGGER = logging.getLogger(__name__)


class ReadableBody(Protocol):
    def read(self) -> bytes: ...


class AgentCoreRuntimeClient(Protocol):
    def invoke_agent_runtime(self, **kwargs: Any) -> dict[str, Any]: ...


def backoff_with_jitter(attempt: int) -> float:
    return min(2.0, 0.2 * (2 ** (attempt - 1))) + random.uniform(0.0, 0.1)


def _read_payload(response: dict[str, Any]) -> bytes:
    body = response.get("payload")
    if body is None:
        raise A2AInvocationError("AgentCore response did not include a payload")
    if isinstance(body, bytes):
        return body
    if isinstance(body, str):
        return body.encode("utf-8")
    read = getattr(body, "read", None)
    if not callable(read):
        raise A2AInvocationError("AgentCore response payload is not readable")
    content = read()
    if not isinstance(content, bytes):
        raise A2AInvocationError("AgentCore response payload did not return bytes")
    return content


@dataclass
class SubagentClient:
    runtime_arn: str
    client: AgentCoreRuntimeClient
    max_attempts: int = 3
    sleep: Callable[[float], None] = time.sleep

    def ask(self, request: str) -> str:
        payload = build_message_send_request(request)
        session_id = str(uuid.uuid4())
        started = time.monotonic()

        for attempt in range(1, self.max_attempts + 1):
            try:
                response = self.client.invoke_agent_runtime(
                    agentRuntimeArn=self.runtime_arn,
                    runtimeSessionId=session_id,
                    contentType="application/json",
                    accept="application/json",
                    payload=json.dumps(payload).encode("utf-8"),
                )
                answer = parse_a2a_response(_read_payload(response))
                LOGGER.info(
                    json.dumps(
                        {
                            "event": "specialist_invocation",
                            "delegated_to_subagent": True,
                            "target_runtime_id": self.runtime_arn.rsplit("/", 1)[-1],
                            "session_id": session_id,
                            "attempt": attempt,
                            "latency_ms": round((time.monotonic() - started) * 1000),
                            "outcome": "success",
                        }
                    )
                )
                return answer
            except A2AInvocationError as exc:
                if not exc.retryable or attempt >= self.max_attempts:
                    LOGGER.exception(
                        "Specialist invocation failed after %s attempt(s)", attempt
                    )
                    raise
                self.sleep(backoff_with_jitter(attempt))

        raise AssertionError("Unreachable retry state")
