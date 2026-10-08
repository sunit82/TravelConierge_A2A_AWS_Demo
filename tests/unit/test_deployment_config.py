from __future__ import annotations

import pytest

from infrastructure.config import DeploymentConfig


def test_accepts_valid_deployment_config() -> None:
    config = DeploymentConfig(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        invoker_principal_arn="arn:aws:iam::123456789012:role/Developer",
        pip_index_url="https://packagefeedproxy.microsoft.io/pypi/simple/",
    )

    assert config.main_runtime_name == "TravelConciergeMain"
    assert config.pip_index_url == "https://packagefeedproxy.microsoft.io/pypi/simple/"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("model_id", ""),
        ("invoker_principal_arn", "not-an-arn"),
        ("main_runtime_name", "invalid-name"),
        ("weather_runtime_name", "1Invalid"),
        ("pip_index_url", "http://insecure.example.com/simple/"),
    ],
)
def test_rejects_invalid_deployment_config(field: str, value: str) -> None:
    values = {
        "model_id": "model",
        "invoker_principal_arn": "arn:aws:iam::123456789012:user/Developer",
        "main_runtime_name": "MainRuntime",
        "weather_runtime_name": "WeatherRuntime",
        "pip_index_url": None,
    }
    values[field] = value

    with pytest.raises(ValueError):
        DeploymentConfig(**values)
