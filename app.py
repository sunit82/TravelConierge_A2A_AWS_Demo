from __future__ import annotations

import aws_cdk as cdk

from infrastructure.agentcore_stack import AgentCoreA2ATravelStack
from infrastructure.config import DeploymentConfig

app = cdk.App()
config = DeploymentConfig.from_cdk(app)

AgentCoreA2ATravelStack(
    app,
    "AgentCoreA2ATravelDemo",
    config=config,
    env=cdk.Environment(
        account=app.node.try_get_context("account") or cdk.Aws.ACCOUNT_ID,
        region=app.node.try_get_context("region") or cdk.Aws.REGION,
    ),
)
app.synth()

