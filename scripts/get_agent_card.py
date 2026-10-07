from __future__ import annotations

import argparse
import json
import uuid
from typing import Any

from scripts.aws_session import assumed_runtime_client


def get_agent_card(runtime_arn: str, role_arn: str, qualifier: str = "DEFAULT") -> Any:
    client = assumed_runtime_client(runtime_arn, role_arn)
    response = client.get_agent_card(
        agentRuntimeArn=runtime_arn,
        runtimeSessionId=str(uuid.uuid4()),
        qualifier=qualifier,
    )
    status = response.get("statusCode")
    if status != 200:
        raise RuntimeError(f"Agent Card request returned HTTP status {status}")
    card = response.get("agentCard")
    if not isinstance(card, dict):
        raise RuntimeError("Agent Card response did not contain an agentCard object")
    return card


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Retrieve an AgentCore A2A Agent Card")
    parser.add_argument("--runtime-arn", required=True)
    parser.add_argument("--role-arn", required=True)
    parser.add_argument("--qualifier", default="DEFAULT")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    card = get_agent_card(args.runtime_arn, args.role_arn, args.qualifier)
    print(json.dumps(card, indent=2, default=str))


if __name__ == "__main__":
    main()

