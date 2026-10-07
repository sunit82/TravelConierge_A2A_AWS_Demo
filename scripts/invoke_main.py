from __future__ import annotations

import argparse
import json
import uuid
from typing import Any

from agents.common.a2a_models import build_message_send_request
from agents.common.response_parser import parse_a2a_response
from agents.main_agent.subagent_client import _read_payload
from scripts.aws_session import assumed_runtime_client


def invoke(
    runtime_arn: str,
    role_arn: str,
    prompt: str,
) -> tuple[str, dict[str, Any]]:
    client = assumed_runtime_client(runtime_arn, role_arn)
    request = build_message_send_request(prompt)
    response = client.invoke_agent_runtime(
        agentRuntimeArn=runtime_arn,
        runtimeSessionId=str(uuid.uuid4()),
        contentType="application/json",
        accept="application/json",
        payload=json.dumps(request).encode("utf-8"),
    )
    payload = _read_payload(response)
    return parse_a2a_response(payload), json.loads(payload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Invoke the main travel concierge")
    parser.add_argument("--runtime-arn", required=True)
    parser.add_argument("--role-arn", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--raw", action="store_true", help="Print raw JSON response")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    answer, raw = invoke(args.runtime_arn, args.role_arn, args.prompt)
    if args.raw:
        print(json.dumps(raw, indent=2))
    else:
        print(answer)


if __name__ == "__main__":
    main()

