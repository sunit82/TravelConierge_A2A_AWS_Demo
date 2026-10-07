from __future__ import annotations

import re
from typing import Any

import boto3
from botocore.config import Config

_RUNTIME_ARN = re.compile(
    r"^arn:(?P<partition>aws(?:-us-gov|-cn)?):bedrock-agentcore:"
    r"(?P<region>[a-z0-9-]+):(?P<account>\d{12}):runtime/(?P<runtime>[A-Za-z0-9_-]+)$"
)


def runtime_region(runtime_arn: str) -> str:
    match = _RUNTIME_ARN.fullmatch(runtime_arn)
    if match is None:
        raise ValueError("runtime ARN is not a valid Bedrock AgentCore runtime ARN")
    return match.group("region")


def assumed_runtime_client(runtime_arn: str, role_arn: str) -> Any:
    region = runtime_region(runtime_arn)
    sts = boto3.client("sts", region_name=region)
    credentials = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName="agentcore-a2a-travel-demo",
        DurationSeconds=3600,
    )["Credentials"]
    return boto3.client(
        "bedrock-agentcore",
        region_name=region,
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
        config=Config(retries={"mode": "standard", "max_attempts": 3}),
    )

