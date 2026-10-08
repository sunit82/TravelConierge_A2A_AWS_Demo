from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_RUNTIME_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,47}$")
_PRINCIPAL_ARN = re.compile(
    r"^arn:(?:aws|aws-us-gov|aws-cn):iam::\d{12}:(?:role|user)/[\w+=,.@/-]+$"
)


@dataclass(frozen=True)
class DeploymentConfig:
    model_id: str
    invoker_principal_arn: str
    main_runtime_name: str = "TravelConciergeMain"
    weather_runtime_name: str = "WeatherPackingSpecialist"
    pip_index_url: str | None = None

    def __post_init__(self) -> None:
        if not self.model_id.strip():
            raise ValueError("CDK context modelId is required and must not be blank")
        if self.pip_index_url is not None and not self.pip_index_url.startswith(
            "https://"
        ):
            raise ValueError("CDK context pipIndexUrl must be an HTTPS URL")
        if not _PRINCIPAL_ARN.fullmatch(self.invoker_principal_arn):
            raise ValueError(
                "CDK context invokerPrincipalArn must be an IAM user or role ARN"
            )
        for label, value in (
            ("mainRuntimeName", self.main_runtime_name),
            ("weatherRuntimeName", self.weather_runtime_name),
        ):
            if not _RUNTIME_NAME.fullmatch(value):
                raise ValueError(
                    f"{label} must start with a letter, contain only letters, "
                    "numbers, or underscores, and be at most 48 characters"
                )
        if self.main_runtime_name == self.weather_runtime_name:
            raise ValueError("Main and weather runtime names must be different")

    @classmethod
    def from_cdk(cls, app: Any) -> DeploymentConfig:
        def context_string(name: str, default: str | None = None) -> str:
            value = app.node.try_get_context(name)
            if value is None:
                if default is not None:
                    return default
                raise ValueError(f"Required CDK context value {name} is missing")
            if not isinstance(value, str):
                raise ValueError(f"CDK context value {name} must be a string")
            return value.strip()

        return cls(
            model_id=context_string("modelId"),
            invoker_principal_arn=context_string("invokerPrincipalArn"),
            main_runtime_name=context_string("mainRuntimeName", "TravelConciergeMain"),
            weather_runtime_name=context_string(
                "weatherRuntimeName", "WeatherPackingSpecialist"
            ),
            pip_index_url=(
                context_string("pipIndexUrl")
                if app.node.try_get_context("pipIndexUrl") is not None
                else None
            ),
        )
