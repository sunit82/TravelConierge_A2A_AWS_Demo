from __future__ import annotations

import os
import re
from dataclasses import dataclass


class ConfigurationError(RuntimeError):
    """Raised when required runtime configuration is missing or invalid."""


_RUNTIME_ARN_PATTERN = re.compile(
    r"^arn:(?P<partition>aws(?:-us-gov|-cn)?):bedrock-agentcore:"
    r"(?P<region>[a-z0-9-]+):(?P<account>\d{12}):runtime/(?P<runtime>[A-Za-z0-9_-]+)$"
)


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigurationError(f"Required environment variable {name} is not set")
    return value


def parse_runtime_arn(runtime_arn: str) -> re.Match[str]:
    match = _RUNTIME_ARN_PATTERN.fullmatch(runtime_arn)
    if match is None:
        raise ConfigurationError(
            "SUBAGENT_RUNTIME_ARN must be an Amazon Bedrock AgentCore runtime ARN"
        )
    return match


@dataclass(frozen=True)
class BaseAgentSettings:
    aws_region: str
    model_id: str

    @classmethod
    def from_env(cls) -> BaseAgentSettings:
        return cls(
            aws_region=require_env("AWS_REGION"),
            model_id=require_env("MODEL_ID"),
        )


@dataclass(frozen=True)
class MainAgentSettings(BaseAgentSettings):
    subagent_runtime_arn: str

    @classmethod
    def from_env(cls) -> MainAgentSettings:
        base = BaseAgentSettings.from_env()
        runtime_arn = require_env("SUBAGENT_RUNTIME_ARN")
        match = parse_runtime_arn(runtime_arn)
        if match.group("region") != base.aws_region:
            raise ConfigurationError(
                "SUBAGENT_RUNTIME_ARN region must match AWS_REGION for this demo"
            )
        return cls(
            aws_region=base.aws_region,
            model_id=base.model_id,
            subagent_runtime_arn=runtime_arn,
        )

