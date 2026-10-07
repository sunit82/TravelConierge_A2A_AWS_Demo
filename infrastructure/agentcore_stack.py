from __future__ import annotations

from pathlib import Path
from typing import Any

from aws_cdk import (
    Arn,
    ArnComponents,
    CfnOutput,
    Duration,
    Stack,
)
from aws_cdk import (
    aws_bedrockagentcore as agentcore,
)
from aws_cdk import (
    aws_ecr_assets as ecr_assets,
)
from aws_cdk import (
    aws_iam as iam,
)
from constructs import Construct

from infrastructure.config import DeploymentConfig

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class AgentCoreA2ATravelStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        config: DeploymentConfig,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        weather_role = self._execution_role("WeatherExecutionRole", config.model_id)
        main_role = self._execution_role("MainExecutionRole", config.model_id)

        weather_runtime = agentcore.Runtime(
            self,
            "WeatherRuntime",
            runtime_name=config.weather_runtime_name,
            description="Deterministic weather and packing specialist",
            agent_runtime_artifact=agentcore.AgentRuntimeArtifact.from_asset(
                str(PROJECT_ROOT),
                file="agents/weather_agent/Dockerfile",
                platform=ecr_assets.Platform.LINUX_ARM64,
            ),
            protocol_configuration=agentcore.ProtocolType.A2_A,
            authorizer_configuration=agentcore.RuntimeAuthorizerConfiguration.using_iam(),
            execution_role=weather_role,
            network_configuration=agentcore.RuntimeNetworkConfiguration.using_public_network(),
            environment_variables={"MODEL_ID": config.model_id},
            tracing_enabled=True,
        )

        main_runtime = agentcore.Runtime(
            self,
            "MainRuntime",
            runtime_name=config.main_runtime_name,
            description="General travel concierge with an A2A weather specialist",
            agent_runtime_artifact=agentcore.AgentRuntimeArtifact.from_asset(
                str(PROJECT_ROOT),
                file="agents/main_agent/Dockerfile",
                platform=ecr_assets.Platform.LINUX_ARM64,
            ),
            protocol_configuration=agentcore.ProtocolType.A2_A,
            authorizer_configuration=agentcore.RuntimeAuthorizerConfiguration.using_iam(),
            execution_role=main_role,
            network_configuration=agentcore.RuntimeNetworkConfiguration.using_public_network(),
            environment_variables={
                "MODEL_ID": config.model_id,
                "SUBAGENT_RUNTIME_ARN": weather_runtime.agent_runtime_arn,
            },
            tracing_enabled=True,
        )
        weather_runtime.grant_invoke_runtime(main_role)

        demo_invoker_role = iam.Role(
            self,
            "DemoInvokerRole",
            description="Assumable role that may invoke only the main travel concierge",
            assumed_by=iam.ArnPrincipal(config.invoker_principal_arn),
            max_session_duration=Duration.hours(1),
        )
        main_runtime.grant_invoke_runtime(demo_invoker_role)

        CfnOutput(self, "MainRuntimeArn", value=main_runtime.agent_runtime_arn)
        CfnOutput(self, "WeatherRuntimeArn", value=weather_runtime.agent_runtime_arn)
        CfnOutput(self, "DemoInvokerRoleArn", value=demo_invoker_role.role_arn)
        CfnOutput(self, "Region", value=self.region)
        CfnOutput(
            self,
            "RuntimeLogGroupPrefix",
            value="/aws/bedrock-agentcore/runtimes/",
        )

    def _execution_role(self, construct_id: str, model_id: str) -> iam.Role:
        role = iam.Role(
            self,
            construct_id,
            assumed_by=iam.ServicePrincipal("bedrock-agentcore.amazonaws.com").with_conditions(
                {
                    "StringEquals": {"aws:SourceAccount": self.account},
                    "ArnLike": {
                        "aws:SourceArn": Arn.format(
                            ArnComponents(
                                service="bedrock-agentcore",
                                resource="*",
                            ),
                            self,
                        )
                    },
                }
            ),
        )

        role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                resources=self._model_resources(model_id),
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "xray:PutTraceSegments",
                    "xray:PutTelemetryRecords",
                ],
                resources=["*"],
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                actions=["cloudwatch:PutMetricData"],
                resources=["*"],
                conditions={
                    "StringEquals": {"cloudwatch:namespace": "bedrock-agentcore"}
                },
            )
        )
        return role

    def _model_resources(self, model_id: str) -> list[str]:
        if model_id.startswith("arn:"):
            resources = [model_id]
        else:
            resources = [
                Arn.format(
                    ArnComponents(
                        service="bedrock",
                        region=self.region,
                        account="",
                        resource="foundation-model",
                        resource_name=model_id,
                        arn_format=None,
                    ),
                    self,
                ),
                Arn.format(
                    ArnComponents(
                        service="bedrock",
                        region=self.region,
                        resource="inference-profile",
                        resource_name=model_id,
                    ),
                    self,
                ),
                Arn.format(
                    ArnComponents(
                        service="bedrock",
                        region=self.region,
                        resource="application-inference-profile",
                        resource_name=model_id,
                    ),
                    self,
                ),
            ]

        # Cross-region profiles invoke regional foundation models whose generated
        # model suffix is not knowable from the opaque profile ID at synth time.
        if "." in model_id and not model_id.startswith("arn:"):
            resources.append(
                Arn.format(
                    ArnComponents(
                        service="bedrock",
                        region="*",
                        account="",
                        resource="foundation-model",
                        resource_name="*",
                    ),
                    self,
                )
            )
        return resources
