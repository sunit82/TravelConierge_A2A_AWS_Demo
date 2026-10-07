from __future__ import annotations

import boto3
from bedrock_agentcore.runtime import serve_a2a
from botocore.config import Config
from strands.multiagent.a2a.executor import StrandsA2AExecutor

from agents.common.config import MainAgentSettings
from agents.main_agent.agent import create_main_agent
from agents.main_agent.subagent_client import SubagentClient


def main() -> None:
    settings = MainAgentSettings.from_env()
    runtime_client = boto3.client(
        "bedrock-agentcore",
        region_name=settings.aws_region,
        config=Config(retries={"mode": "standard", "max_attempts": 3}),
    )
    specialist = SubagentClient(
        runtime_arn=settings.subagent_runtime_arn,
        client=runtime_client,
    )
    serve_a2a(StrandsA2AExecutor(create_main_agent(settings.model_id, specialist.ask)))


if __name__ == "__main__":
    main()
