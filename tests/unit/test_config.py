import pytest

from agents.common.config import ConfigurationError, MainAgentSettings


def test_main_settings_load_valid_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("MODEL_ID", "model-id")
    monkeypatch.setenv(
        "SUBAGENT_RUNTIME_ARN",
        "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/WeatherAgent-abc",
    )

    settings = MainAgentSettings.from_env()

    assert settings.aws_region == "us-east-1"
    assert settings.model_id == "model-id"


def test_main_settings_reject_cross_region_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_REGION", "us-west-2")
    monkeypatch.setenv("MODEL_ID", "model-id")
    monkeypatch.setenv(
        "SUBAGENT_RUNTIME_ARN",
        "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/WeatherAgent-abc",
    )

    with pytest.raises(ConfigurationError, match="region"):
        MainAgentSettings.from_env()

