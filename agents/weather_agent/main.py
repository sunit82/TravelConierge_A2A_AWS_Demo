from __future__ import annotations

from bedrock_agentcore.runtime import serve_a2a
from strands.multiagent.a2a.executor import StrandsA2AExecutor

from agents.common.config import BaseAgentSettings
from agents.weather_agent.agent import create_weather_agent


def main() -> None:
    settings = BaseAgentSettings.from_env()
    serve_a2a(StrandsA2AExecutor(create_weather_agent(settings.model_id)))


if __name__ == "__main__":
    main()
