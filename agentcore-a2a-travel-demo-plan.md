# Plan: A2A Travel Concierge on Amazon Bedrock AgentCore

## 1. Objective

Build a reproducible Python demo with two independently hosted Amazon Bedrock AgentCore Runtime agents:

- **Main agent — Travel Concierge**: answers general travel questions itself and decides, through model tool selection, when specialist help is required.
- **Subagent — Weather and Packing Specialist**: accepts A2A `message/send` requests, looks up deterministic demo weather fixtures, and returns weather-aware packing advice.

When the main agent decides specialist knowledge is needed, it invokes the subagent through Amazon Bedrock AgentCore's `InvokeAgentRuntime` API. The invocation body remains a standard A2A JSON-RPC 2.0 request, so AgentCore acts as the authenticated A2A transport/proxy. When specialist knowledge is unnecessary, the main agent answers without invoking the A2A tool.

The demo will be:

- Provisioned with **AWS CDK in Python**.
- Packaged as two **ARM64 container images** built by CDK.
- Hosted as two distinct **AgentCore Runtime** resources using protocol type `A2A`.
- Protected with **AWS IAM/SigV4**.
- Configurable for any region and any compatible Amazon Bedrock model or inference profile.
- Observable through CloudWatch Logs, metrics, and X-Ray tracing.
- Testable locally without AWS calls by injecting a fake subagent client and deterministic weather fixtures.

## 2. Confirmed Design Decisions

| Decision | Selection |
|---|---|
| Infrastructure as code | AWS CDK v2, Python |
| Agent framework | Strands Agents |
| Agent protocol | A2A JSON-RPC 2.0 |
| Hosting | Amazon Bedrock AgentCore Runtime |
| Runtime authentication | AWS IAM/SigV4 |
| Region | CDK deployment region; no region hard-coded |
| Model | Required deployment parameter; model ID or inference-profile ID |
| Main agent role | General travel concierge |
| Subagent role | Destination weather and packing specialist |
| Weather source | Deterministic fixture data, with no external API dependency |
| Runtime networking | Public network mode; no VPC/NAT required for the demo |
| Packaging | ARM64 Docker image asset per agent |
| Main-to-subagent transport | Boto3 `bedrock-agentcore.invoke_agent_runtime` carrying an A2A payload |
| Main routing behavior | LLM tool selection, reinforced by a narrow tool description and system prompt |

## 3. Architecture

```text
Developer / Demo Caller
  |
  | Assume DemoInvokerRole, then SigV4 InvokeAgentRuntime
  | A2A JSON-RPC: message/send
  v
+-----------------------------------------------+
| AgentCore Runtime: TravelConciergeMain        |
| Protocol: A2A                                 |
| Auth: IAM                                     |
|                                               |
| Strands Agent                                 |
| - General travel knowledge                    |
| - Tool: consult_weather_packing_specialist    |
|                                               |
| Decision A: no specialist needed              |
|   -> respond directly                         |
|                                               |
| Decision B: weather/packing needed            |
|   -> invoke tool                              |
+------------------------+----------------------+
                         |
                         | Main execution role signs
                         | bedrock-agentcore:InvokeAgentRuntime
                         | A2A JSON-RPC: message/send
                         v
+-----------------------------------------------+
| AgentCore Runtime: WeatherPackingSpecialist   |
| Protocol: A2A                                 |
| Auth: IAM                                     |
|                                               |
| Strands Agent                                 |
| - Tool: lookup_demo_weather                   |
| - Deterministic weather fixtures              |
| - Packing recommendations                     |
+-----------------------------------------------+

Both runtimes:
- Invoke the configured Bedrock model/inference profile.
- Emit logs and telemetry to CloudWatch/X-Ray.
- Serve POST /, GET /ping, and GET /.well-known/agent-card.json.
```

### Request sequence when delegation is required

1. The caller assumes `DemoInvokerRole`.
2. The caller sends an A2A `message/send` JSON-RPC request to the main runtime with `boto3`.
3. AgentCore verifies SigV4 and forwards the unmodified JSON-RPC body to the main container.
4. `serve_a2a` and `StrandsA2AExecutor` deliver the user message to the main Strands agent.
5. The model sees that the question depends on weather or packing and selects `consult_weather_packing_specialist`.
6. The tool builds a new A2A `message/send` request and calls the subagent runtime through the AgentCore boto3 client.
7. The subagent uses `lookup_demo_weather`, creates packing advice, and returns an A2A result.
8. The main tool extracts text from the A2A response.
9. The main agent incorporates the specialist answer and returns its final A2A response to the caller.

### Request sequence when delegation is not required

1. Steps 1–4 are the same.
2. The model determines that the prompt is general travel knowledge, such as explaining the difference between a direct and connecting flight.
3. The model does not select the specialist tool.
4. The main agent responds directly.
5. A test spy and a structured `delegated_to_subagent` log field prove that no subagent call occurred.

## 4. AWS and Protocol Constraints the Implementation Will Honor

- A2A containers listen on `0.0.0.0:9000`.
- A2A JSON-RPC is served at `POST /`.
- Agent discovery is served at `GET /.well-known/agent-card.json`.
- Health is served at `GET /ping`.
- AgentCore injects and manages the runtime session header.
- Container images must be compatible with ARM64.
- Both runtimes use `ProtocolType.A2A`.
- Both runtimes use `RuntimeAuthorizerConfiguration.iam()`.
- The main execution role receives only `bedrock-agentcore:InvokeAgentRuntime` on the subagent runtime.
- The subagent receives no permission to invoke the main runtime.
- The demo invoker role receives only `bedrock-agentcore:InvokeAgentRuntime` on the main runtime.
- The main runtime is not used as a proxy for arbitrary runtime ARNs; the subagent ARN comes only from a deployment environment variable.
- JSON-RPC errors are parsed even when AgentCore returns a non-2xx HTTP status.
- HTTP 409 / JSON-RPC `-32054` retryable session conflicts use bounded exponential backoff with jitter.
- The implementation will not update health timestamps on every ping; `serve_a2a` owns the health contract.

## 5. Planned Repository Layout

```text
agentcore-a2a-travel-demo/
|-- README.md
|-- pyproject.toml
|-- requirements-dev.txt
|-- .gitignore
|-- cdk.json
|-- app.py
|-- agents/
|   |-- common/
|   |   |-- __init__.py
|   |   |-- config.py
|   |   |-- a2a_models.py
|   |   `-- response_parser.py
|   |-- main_agent/
|   |   |-- Dockerfile
|   |   |-- requirements.txt
|   |   |-- main.py
|   |   |-- agent.py
|   |   `-- subagent_client.py
|   `-- weather_agent/
|       |-- Dockerfile
|       |-- requirements.txt
|       |-- main.py
|       |-- agent.py
|       |-- weather_tool.py
|       `-- weather_fixtures.py
|-- infrastructure/
|   |-- __init__.py
|   |-- config.py
|   `-- agentcore_stack.py
|-- scripts/
|   |-- invoke_main.py
|   |-- get_agent_card.py
|   `-- smoke_test.py
`-- tests/
    |-- unit/
    |   |-- test_weather_tool.py
    |   |-- test_response_parser.py
    |   |-- test_subagent_client.py
    |   `-- test_main_routing.py
    `-- integration/
        `-- test_deployed_agents.py
```

## 6. Detailed File-by-File Code Plan

### 6.1 Root project files

#### `pyproject.toml`

Purpose:

- Defines the infrastructure, scripts, and test project.
- Pins compatible dependency ranges so a future SDK breaking change does not silently alter protocol behavior.
- Configures pytest, Ruff, and mypy.

Planned dependency groups:

```toml
[project]
name = "agentcore-a2a-travel-demo"
requires-python = ">=3.12,<3.13"
dependencies = [
  "aws-cdk-lib>=2,<3",
  "constructs>=10,<11",
  "boto3>=1.42,<2",
]

[project.optional-dependencies]
dev = [
  "mypy>=1.15,<2",
  "pytest>=8,<9",
  "pytest-asyncio>=0.26,<2",
  "ruff>=0.11,<1",
]
```

Notes:

- Agent-container dependencies stay in each agent's `requirements.txt` so Docker build contexts remain explicit.
- Exact minimum versions will be selected after checking the current `bedrock-agentcore`, `strands-agents`, `a2a-sdk`, boto3, and CDK releases at implementation time.
- A lock file may be added with the repository's chosen dependency workflow.

#### `requirements-dev.txt`

Purpose:

- Offers a simple `pip install -r requirements-dev.txt` path in addition to installing the project extras.

Planned contents reference the editable project:

```text
-e .[dev]
```

#### `.gitignore`

Ignores:

- `.venv/`
- `__pycache__/`
- `.pytest_cache/`
- `.mypy_cache/`
- `.ruff_cache/`
- `cdk.out/`
- `.env`
- generated test output

It will not ignore source fixtures or CDK configuration required to reproduce the demo.

#### `cdk.json`

Purpose:

- Declares `python app.py` as the CDK app.
- Documents required context keys:
  - `modelId`
  - `invokerPrincipalArn`
- Supports optional context:
  - `mainRuntimeName`
  - `weatherRuntimeName`

Example:

```json
{
  "app": "python app.py",
  "context": {
    "mainRuntimeName": "TravelConciergeMain",
    "weatherRuntimeName": "WeatherPackingSpecialist"
  }
}
```

Sensitive values will not be stored in this file.

#### `app.py`

Purpose:

- Loads and validates CDK context.
- Uses `CDK_DEFAULT_ACCOUNT` and `CDK_DEFAULT_REGION`.
- Instantiates `AgentCoreA2ATravelStack`.

Planned shape:

```python
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
        account=app.node.try_get_context("account")
        or cdk.Aws.ACCOUNT_ID,
        region=app.node.try_get_context("region")
        or cdk.Aws.REGION,
    ),
)
app.synth()
```

`DeploymentConfig.from_cdk` will fail with an actionable message when `modelId` or `invokerPrincipalArn` is absent.

#### `README.md`

Contains:

- Architecture and delegation explanation.
- Prerequisites and exact setup commands.
- Region/model selection guidance.
- CDK deploy commands.
- Local unit-test commands.
- Agent-card and smoke-test commands.
- Delegation and non-delegation sample prompts.
- CloudWatch/X-Ray verification.
- Troubleshooting for model access, ARM64 Docker builds, IAM denial, and session conflict.
- Cleanup command.
- Cost and production-hardening notes.

### 6.2 Shared agent modules

The Docker build contexts will copy `agents/common` into both images.

#### `agents/common/__init__.py`

Marks shared code as a package. It will not contain side effects.

#### `agents/common/config.py`

Purpose:

- Loads runtime environment variables.
- Rejects missing or malformed values.
- Keeps model and runtime identifiers out of source code.

Planned types:

```python
from dataclasses import dataclass
import os


class ConfigurationError(RuntimeError):
    pass


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigurationError(f"Required environment variable {name} is not set")
    return value


@dataclass(frozen=True)
class BaseAgentSettings:
    aws_region: str
    model_id: str

    @classmethod
    def from_env(cls) -> "BaseAgentSettings":
        return cls(
            aws_region=require_env("AWS_REGION"),
            model_id=require_env("MODEL_ID"),
        )


@dataclass(frozen=True)
class MainAgentSettings(BaseAgentSettings):
    subagent_runtime_arn: str

    @classmethod
    def from_env(cls) -> "MainAgentSettings":
        base = BaseAgentSettings.from_env()
        return cls(
            aws_region=base.aws_region,
            model_id=base.model_id,
            subagent_runtime_arn=require_env("SUBAGENT_RUNTIME_ARN"),
        )
```

Additional validation:

- `SUBAGENT_RUNTIME_ARN` must parse as an AgentCore runtime ARN.
- The ARN region and account must match the current deployment unless an explicit future cross-account mode is added.

#### `agents/common/a2a_models.py`

Purpose:

- Centralizes the minimal JSON-RPC structures the boto3 transport needs.
- Generates UUID message and request IDs.
- Prevents hand-built dictionaries from drifting across scripts and agents.

Planned models/functions:

```python
from typing import NotRequired, TypedDict


class TextPart(TypedDict):
    kind: str
    text: str


class A2AMessage(TypedDict):
    role: str
    parts: list[TextPart]
    messageId: str


class MessageSendParams(TypedDict):
    message: A2AMessage


class JsonRpcRequest(TypedDict):
    jsonrpc: str
    id: str
    method: str
    params: MessageSendParams


def build_message_send_request(text: str) -> JsonRpcRequest:
    ...
```

`build_message_send_request` will:

- Reject blank input.
- Set `jsonrpc` to `"2.0"`.
- Set `method` to `"message/send"`.
- Set message role to `"user"`.
- Add one A2A text part with `kind: "text"`.

#### `agents/common/response_parser.py`

Purpose:

- Reads the AgentCore response stream.
- Parses the JSON body.
- Detects JSON-RPC errors on both successful and non-successful HTTP responses.
- Extracts text from valid A2A task artifacts or direct message results.

Planned public API:

```python
class A2AInvocationError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        json_rpc_code: int | None = None,
        retryable: bool = False,
    ) -> None:
        ...


def parse_a2a_response(payload: bytes) -> str:
    ...
```

Parsing behavior:

- Return joined text parts from `result.artifacts[*].parts[*]`.
- Also accept a direct A2A message result for SDK compatibility.
- Raise `A2AInvocationError` if:
  - JSON decoding fails.
  - A JSON-RPC `error` exists.
  - No text artifact exists.
- Mark code `-32054` with message `Session operation in progress` as retryable.
- Never return an empty success-shaped response.

### 6.3 Weather and packing subagent

#### `agents/weather_agent/requirements.txt`

Planned runtime dependencies:

```text
bedrock-agentcore>=1,<2
strands-agents>=1,<2
```

The exact compatible versions will be pinned during implementation after a local build/test.

#### `agents/weather_agent/Dockerfile`

Purpose:

- Produces an ARM64-compatible runtime image.
- Installs only subagent dependencies.
- Runs as a non-root user where the selected AgentCore base-image/runtime contract permits it.
- Starts `main.py`, which starts the A2A server on port 9000.

Planned structure:

```dockerfile
FROM public.ecr.aws/docker/library/python:3.12-slim

WORKDIR /app
COPY agents/weather_agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY agents/common ./agents/common
COPY agents/weather_agent ./agents/weather_agent
ENV PYTHONUNBUFFERED=1
EXPOSE 9000
CMD ["python", "-m", "agents.weather_agent.main"]
```

CDK will build it using Linux ARM64. A `.dockerignore` will be added if the chosen root build context requires excluding local caches and `cdk.out`.

#### `agents/weather_agent/weather_fixtures.py`

Purpose:

- Stores deterministic demo conditions for known city/month combinations.
- Keeps data separate from tool behavior.

Planned type and sample records:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class WeatherFixture:
    destination: str
    month: int
    summary: str
    low_c: int
    high_c: int
    rain_likelihood: str
    conditions: tuple[str, ...]


WEATHER_FIXTURES = {
    ("tokyo", 4): WeatherFixture(
        destination="Tokyo",
        month=4,
        summary="Mild spring weather with changeable rain",
        low_c=10,
        high_c=19,
        rain_likelihood="moderate",
        conditions=("mild", "showers"),
    ),
    ("reykjavik", 12): WeatherFixture(...),
    ("singapore", 7): WeatherFixture(...),
}
```

Fallback behavior:

- Unknown destination/month combinations return a clearly labeled **demo climatology fallback**, not invented live weather.
- The result explicitly states that the data is deterministic demo data.
- Invalid month values fail validation.

#### `agents/weather_agent/weather_tool.py`

Purpose:

- Exposes the specialist's deterministic weather lookup as a Strands tool.

Planned API:

```python
from strands import tool


@tool
def lookup_demo_weather(destination: str, month: int) -> str:
    """Return deterministic demo weather for a destination and travel month."""
    fixture = find_fixture(destination, month)
    return (
        f"DEMO WEATHER DATA for {fixture.destination}: "
        f"{fixture.summary}; {fixture.low_c}-{fixture.high_c} C; "
        f"rain likelihood: {fixture.rain_likelihood}; "
        f"conditions: {', '.join(fixture.conditions)}."
    )
```

Validation:

- Destination is stripped, normalized, and length-limited.
- Month must be 1–12.
- Output always identifies itself as demo data.

#### `agents/weather_agent/agent.py`

Purpose:

- Constructs the specialist Strands agent.
- Defines the specialist's boundaries and response contract.

Planned system prompt:

```text
You are the Weather and Packing Specialist for a travel concierge.
Handle only destination weather context and weather-aware packing advice.
Always call lookup_demo_weather before making weather claims.
Clearly label all weather values as deterministic demo data, not a live forecast.
Return a concise response with:
1. Conditions
2. Essential clothing
3. Weather-specific accessories
4. One practical caution
If the request is outside your specialty, say so rather than inventing an answer.
```

Planned constructor:

```python
from strands import Agent

from agents.weather_agent.weather_tool import lookup_demo_weather


def create_weather_agent(model_id: str) -> Agent:
    return Agent(
        model=model_id,
        system_prompt=WEATHER_AGENT_PROMPT,
        tools=[lookup_demo_weather],
    )
```

If the current Strands version requires an explicit Bedrock model provider object, the constructor will use the supported `BedrockModel` class rather than passing the ID directly.

#### `agents/weather_agent/main.py`

Purpose:

- Creates the subagent and exposes it as an AgentCore-compatible A2A server.

Planned code:

```python
from bedrock_agentcore.runtime import serve_a2a
from strands.multiagent.a2a.executor import StrandsA2AExecutor

from agents.common.config import BaseAgentSettings
from agents.weather_agent.agent import create_weather_agent


def main() -> None:
    settings = BaseAgentSettings.from_env()
    agent = create_weather_agent(settings.model_id)
    serve_a2a(StrandsA2AExecutor(agent))


if __name__ == "__main__":
    main()
```

`serve_a2a` owns:

- Port 9000 binding.
- `/ping`.
- `/.well-known/agent-card.json`.
- Runtime URL and AgentCore header handling.

### 6.4 Main travel concierge

#### `agents/main_agent/requirements.txt`

Planned runtime dependencies:

```text
bedrock-agentcore>=1,<2
boto3>=1.42,<2
strands-agents>=1,<2
```

The main container does not need a general-purpose HTTP client because boto3 performs SigV4 and invokes the managed runtime API.

#### `agents/main_agent/Dockerfile`

Matches the subagent image strategy but copies `agents/main_agent`.

```dockerfile
FROM public.ecr.aws/docker/library/python:3.12-slim

WORKDIR /app
COPY agents/main_agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY agents/common ./agents/common
COPY agents/main_agent ./agents/main_agent
ENV PYTHONUNBUFFERED=1
EXPOSE 9000
CMD ["python", "-m", "agents.main_agent.main"]
```

CDK builds it as Linux ARM64.

#### `agents/main_agent/subagent_client.py`

Purpose:

- Encapsulates the authenticated A2A call to the weather runtime.
- Makes the main agent tool small and unit-testable.

Planned design:

```python
from dataclasses import dataclass
import json
import random
import time
from typing import Protocol
import uuid

import boto3

from agents.common.a2a_models import build_message_send_request
from agents.common.response_parser import A2AInvocationError, parse_a2a_response


class AgentCoreRuntimeClient(Protocol):
    def invoke_agent_runtime(self, **kwargs: object) -> dict[str, object]:
        ...


@dataclass
class SubagentClient:
    runtime_arn: str
    client: AgentCoreRuntimeClient
    max_attempts: int = 3

    def ask(self, request: str) -> str:
        payload = build_message_send_request(request)
        session_id = str(uuid.uuid4())
        for attempt in range(1, self.max_attempts + 1):
            try:
                response = self.client.invoke_agent_runtime(
                    agentRuntimeArn=self.runtime_arn,
                    runtimeSessionId=session_id,
                    contentType="application/json",
                    accept="application/json",
                    payload=json.dumps(payload).encode("utf-8"),
                )
                body = response["response"].read()
                return parse_a2a_response(body)
            except A2AInvocationError as exc:
                if not exc.retryable or attempt == self.max_attempts:
                    raise
                time.sleep(backoff_with_jitter(attempt))
        raise AssertionError("unreachable")
```

Implementation details:

- `boto3.client("bedrock-agentcore", region_name=...)` supplies SigV4 automatically from the main runtime's execution-role credentials.
- The subagent ARN is fixed from `SUBAGENT_RUNTIME_ARN`; user text cannot select an ARN.
- Each tool call receives a fresh runtime session ID unless a deliberate conversation-session propagation design is added later.
- The client handles both the current streaming body key used by boto3 and verifies it against the live SDK shape during implementation.
- AWS SDK transport exceptions are logged and re-raised with context; they are not converted into fake specialist answers.
- Retries are limited to documented retryable conflicts and SDK retryable transport errors.
- Logs include request ID, session ID, target runtime ID, latency, and success/failure, but not full user prompts.

#### `agents/main_agent/agent.py`

Purpose:

- Creates the main agent and its narrowly scoped specialist tool.
- Allows a fake client to be injected in tests.

Planned factory:

```python
from collections.abc import Callable

from strands import Agent, tool


MAIN_AGENT_PROMPT = """
You are a general travel concierge.
Answer general travel planning, transport, etiquette, and itinerary questions yourself.

You have one specialist tool for destination weather and weather-aware packing.
Call consult_weather_packing_specialist when the answer depends on:
- destination weather or climate,
- what to pack for expected conditions,
- rain, temperature, seasonal clothing, or weather precautions.

Do not call the specialist for general questions that you can answer directly,
including flight terminology, itinerary structure, travel-document reminders,
general etiquette, or time-zone concepts.

Never claim you called the specialist unless the tool was actually used.
When you use it, preserve its statement that weather values are demo data.
"""


def create_main_agent(model_id: str, ask_specialist: Callable[[str], str]) -> Agent:
    @tool
    def consult_weather_packing_specialist(
        destination: str,
        travel_month: int,
        traveler_context: str = "",
    ) -> str:
        """Use only for destination weather or weather-aware packing advice."""
        request = (
            f"Destination: {destination}\n"
            f"Travel month: {travel_month}\n"
            f"Traveler context: {traveler_context or 'not provided'}\n"
            "Provide conditions and weather-aware packing advice."
        )
        return ask_specialist(request)

    return Agent(
        model=model_id,
        system_prompt=MAIN_AGENT_PROMPT,
        tools=[consult_weather_packing_specialist],
    )
```

Why this causes detection:

- Strands publishes the tool name, description, and typed arguments to the Bedrock model.
- The system prompt defines positive routing criteria and explicit negative criteria.
- The model performs semantic routing through ordinary tool selection.
- No brittle keyword router is inserted in front of the model.
- Unit and deployed integration tests verify both branches.

#### `agents/main_agent/main.py`

Purpose:

- Loads settings.
- Builds the boto3 AgentCore client and `SubagentClient`.
- Builds the main Strands agent.
- Serves it through A2A.

Planned code:

```python
import boto3
from bedrock_agentcore.runtime import serve_a2a
from strands.multiagent.a2a.executor import StrandsA2AExecutor

from agents.common.config import MainAgentSettings
from agents.main_agent.agent import create_main_agent
from agents.main_agent.subagent_client import SubagentClient


def main() -> None:
    settings = MainAgentSettings.from_env()
    runtime_client = boto3.client(
        "bedrock-agentcore",
        region_name=settings.aws_region,
    )
    specialist = SubagentClient(
        runtime_arn=settings.subagent_runtime_arn,
        client=runtime_client,
    )
    agent = create_main_agent(settings.model_id, specialist.ask)
    serve_a2a(StrandsA2AExecutor(agent))


if __name__ == "__main__":
    main()
```

### 6.5 Infrastructure

#### `infrastructure/__init__.py`

Package marker only.

#### `infrastructure/config.py`

Purpose:

- Provides a typed `DeploymentConfig`.
- Validates CDK context before resources are synthesized.

Planned fields:

```python
@dataclass(frozen=True)
class DeploymentConfig:
    model_id: str
    invoker_principal_arn: str
    main_runtime_name: str = "TravelConciergeMain"
    weather_runtime_name: str = "WeatherPackingSpecialist"
```

Validation:

- Runtime names match AgentCore's name rules and length limit.
- Principal ARN is a valid IAM role or user ARN.
- `model_id` is non-empty and is treated as an opaque Bedrock model/inference-profile identifier.

#### `infrastructure/agentcore_stack.py`

Purpose:

- Builds both ARM64 image assets.
- Creates least-privilege execution roles.
- Creates both IAM-authorized A2A AgentCore runtimes.
- Wires the subagent ARN into the main runtime.
- Grants the main runtime permission to invoke only the subagent.
- Creates a dedicated demo caller role trusted only by the configured principal.
- Grants that role permission to invoke only the main runtime.
- Enables tracing and outputs identifiers.

Planned high-level code:

```python
from pathlib import Path

from aws_cdk import (
    Arn,
    ArnComponents,
    CfnOutput,
    Duration,
    Stack,
    aws_bedrockagentcore as agentcore,
    aws_ecr_assets as ecr_assets,
    aws_iam as iam,
)
from constructs import Construct


class AgentCoreA2ATravelStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, config, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        weather_role = self._execution_role("WeatherExecutionRole")
        main_role = self._execution_role("MainExecutionRole")

        weather_runtime = agentcore.Runtime(
            self,
            "WeatherRuntime",
            runtime_name=config.weather_runtime_name,
            agent_runtime_artifact=agentcore.AgentRuntimeArtifact.from_asset(
                str(PROJECT_ROOT),
                options=ecr_assets.DockerImageAssetOptions(
                    file="agents/weather_agent/Dockerfile",
                    platform=ecr_assets.Platform.LINUX_ARM64,
                ),
            ),
            protocol_configuration=agentcore.ProtocolType.A2A,
            authorizer_configuration=agentcore.RuntimeAuthorizerConfiguration.iam(),
            execution_role=weather_role,
            network_configuration=agentcore.RuntimeNetworkConfiguration.using_public_network(),
            environment_variables={
                "MODEL_ID": config.model_id,
            },
            tracing_enabled=True,
        )

        main_runtime = agentcore.Runtime(
            self,
            "MainRuntime",
            runtime_name=config.main_runtime_name,
            agent_runtime_artifact=...,
            protocol_configuration=agentcore.ProtocolType.A2A,
            authorizer_configuration=agentcore.RuntimeAuthorizerConfiguration.iam(),
            execution_role=main_role,
            network_configuration=agentcore.RuntimeNetworkConfiguration.using_public_network(),
            environment_variables={
                "MODEL_ID": config.model_id,
                "SUBAGENT_RUNTIME_ARN": weather_runtime.agent_runtime_arn,
            },
            tracing_enabled=True,
        )

        weather_runtime.grant_invoke_runtime(main_role)
```

The exact Python names generated by jsii will be confirmed against the installed CDK package. In Python, the expected names are snake-case equivalents such as `from_asset`, `using_public_network`, and `grant_invoke_runtime`.

Execution role policy will include:

- Bedrock:
  - `bedrock:InvokeModel`
  - `bedrock:InvokeModelWithResponseStream`
- Resources:
  - Foundation model resources required by the chosen model.
  - Inference profile and application inference profile resources in the deployment account.
  - Destination-region foundation model resources when a cross-region inference profile requires them.
- CloudWatch Logs permissions required by AgentCore Runtime.
- X-Ray trace and telemetry writes.
- `cloudwatch:PutMetricData` constrained to the `bedrock-agentcore` namespace.
- ECR pull permissions are supplied/bound by `AgentRuntimeArtifact.from_asset`; synthesized output will be inspected to confirm.

Trust policy:

```json
{
  "Effect": "Allow",
  "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
  "Action": "sts:AssumeRole",
  "Condition": {
    "StringEquals": {"aws:SourceAccount": "<account>"},
    "ArnLike": {
      "aws:SourceArn": "arn:<partition>:bedrock-agentcore:<region>:<account>:*"
    }
  }
}
```

Demo invoker role:

```python
demo_invoker_role = iam.Role(
    self,
    "DemoInvokerRole",
    assumed_by=iam.ArnPrincipal(config.invoker_principal_arn),
    max_session_duration=Duration.hours(1),
)
main_runtime.grant_invoke_runtime(demo_invoker_role)
```

CDK outputs:

- `MainRuntimeArn`
- `WeatherRuntimeArn`
- `DemoInvokerRoleArn`
- `Region`
- `MainAgentCardUrl`
- CloudWatch log-group names

Deployment dependency:

- The main runtime depends on the weather runtime ARN through its environment variable.
- The invocation grant references the weather runtime.
- CloudFormation therefore creates the subagent before completing the main runtime.

### 6.6 Operational and test scripts

#### `scripts/invoke_main.py`

Purpose:

- Assumes `DemoInvokerRole`.
- Sends a correctly formed A2A request to the main runtime.
- Prints extracted final text.
- Optionally prints the raw JSON response for protocol debugging.

Planned CLI:

```text
python scripts/invoke_main.py \
  --runtime-arn <MainRuntimeArn> \
  --role-arn <DemoInvokerRoleArn> \
  --prompt "I will visit Tokyo in April. What weather should I expect and what should I pack?"
```

Key implementation:

```python
credentials = sts.assume_role(
    RoleArn=args.role_arn,
    RoleSessionName="agentcore-a2a-demo",
)["Credentials"]

client = boto3.client(
    "bedrock-agentcore",
    region_name=runtime_region,
    aws_access_key_id=credentials["AccessKeyId"],
    aws_secret_access_key=credentials["SecretAccessKey"],
    aws_session_token=credentials["SessionToken"],
)

response = client.invoke_agent_runtime(
    agentRuntimeArn=args.runtime_arn,
    runtimeSessionId=str(uuid.uuid4()),
    contentType="application/json",
    accept="application/json",
    payload=json.dumps(build_message_send_request(args.prompt)).encode(),
)
```

The script will:

- Derive and validate the region from the runtime ARN.
- Use a UUID session ID.
- Reuse the shared response parser.
- Return a nonzero exit code on authentication, runtime, A2A, or parsing failure.

#### `scripts/get_agent_card.py`

Purpose:

- Retrieves the deployed main or subagent Agent Card using SigV4.
- Confirms discovery metadata and runtime URL.

Because direct Agent Card retrieval uses the runtime HTTPS URL rather than the JSON-RPC invocation body, this script will:

- Assume the demo role for the main runtime, or use main execution-role credentials only in an explicit diagnostic environment for the subagent.
- Build the URL with the URL-encoded runtime ARN.
- Sign the GET request with botocore SigV4.
- Request `/.well-known/agent-card.json`.
- Validate:
  - Protocol version.
  - JSON-RPC transport.
  - Runtime URL.
  - Agent name and skills.

If the deployed demo role intentionally lacks subagent permission, the standard user workflow fetches only the main card. An administrator may test the subagent card separately.

#### `scripts/smoke_test.py`

Purpose:

- Runs both required examples against the deployed main runtime.
- Produces clear evidence of the routing branch.

Cases:

1. **Delegation expected**

   ```text
   I am visiting Tokyo in April. What weather should I expect, and what should I pack?
   ```

   Expected:
   - Main invokes the specialist.
   - Response mentions deterministic demo data.
   - Response contains weather conditions and packing advice.
   - Main and weather runtime logs share trace/session correlation.

2. **No delegation expected**

   ```text
   Explain the difference between a direct flight and a nonstop flight in two sentences.
   ```

   Expected:
   - Main answers accurately itself.
   - No subagent invocation log is emitted for the request.
   - Weather runtime invocation metric does not increment for this request window.

The script validates response content. CloudWatch verification is documented as a separate deterministic check because metric/log propagation is eventually consistent.

### 6.7 Tests

#### `tests/unit/test_weather_tool.py`

Cases:

- Known city/month returns the expected fixture.
- Output is labeled as demo data.
- Destination normalization works.
- Invalid month raises a clear validation error.
- Unknown fixture uses the documented climatology fallback and does not claim live data.

#### `tests/unit/test_response_parser.py`

Cases:

- Extracts text from task artifacts.
- Extracts text from a direct message result.
- Joins multiple text parts in order.
- Rejects malformed JSON.
- Rejects missing text output.
- Raises a non-retryable error for ordinary JSON-RPC errors.
- Marks documented `-32054` session-operation conflicts retryable.

#### `tests/unit/test_subagent_client.py`

Uses a fake boto3-compatible client.

Cases:

- Sends `jsonrpc: "2.0"` and `method: "message/send"`.
- Uses the configured ARN rather than any prompt-provided ARN.
- Sets content and accept types.
- Uses a runtime session ID.
- Returns parsed specialist text.
- Retries the documented retryable conflict with bounded attempts.
- Does not retry access denied, validation errors, or malformed responses.
- Surfaces SDK failures.

#### `tests/unit/test_main_routing.py`

Uses a deterministic fake model/tool-selection harness or Strands-supported model stub.

Cases:

- Weather/packing prompt calls the injected specialist exactly once.
- General flight terminology prompt calls the specialist zero times.
- A specialist result is incorporated without losing the demo-data disclosure.
- A specialist failure is surfaced as an explicit inability to retrieve specialist advice, not replaced with invented weather.

Because real-model routing is probabilistic, this test validates prompt/tool wiring with a controlled model stub. Deployed integration tests validate actual configured-model behavior.

#### `tests/integration/test_deployed_agents.py`

Opt-in tests guarded by environment variables:

- `MAIN_RUNTIME_ARN`
- `DEMO_INVOKER_ROLE_ARN`
- `AWS_REGION`

Cases:

- Main agent card is retrievable.
- Delegation prompt returns a specialist-derived answer.
- No-delegation prompt returns a direct answer.
- Optional CloudWatch Logs Insights query confirms one subagent invocation for the delegation correlation ID and zero for the direct-answer correlation ID.

Integration tests will not run by default in unit-test CI because they incur AWS charges and require deployed resources.

## 7. AWS Resource Creation and Configuration Steps

### Step 1 — Select a region and model

1. Choose a region where:
   - Amazon Bedrock AgentCore Runtime is available.
   - The selected Bedrock model or inference profile is usable.
2. List available inference profiles:

   ```powershell
   aws bedrock list-inference-profiles --region <region>
   ```

3. Choose either:
   - A supported foundation model ID, or
   - A system/application inference-profile ID or ARN.
4. Verify the account can invoke it with a minimal Bedrock test before deploying the agents.
5. Record the exact identifier as `modelId`.

The plan intentionally does not hard-code a model because model availability and recommended inference profiles differ by region and account.

### Step 2 — Prepare local tooling

Required:

- AWS account and credentials.
- AWS CLI v2.
- Python 3.12.
- Node.js and npm for AWS CDK CLI.
- Docker Desktop with Linux container and ARM64 build support.
- AWS CDK v2:

  ```powershell
  npm install -g aws-cdk
  ```

- Optional AgentCore CLI for interactive A2A inspection:

  ```powershell
  npm install -g @aws/agentcore
  ```

Configure credentials:

```powershell
aws configure sso
aws sts get-caller-identity
```

The deploying identity needs permissions for CloudFormation, CDK bootstrap assets, IAM role creation/passing, ECR, CloudWatch/X-Ray policy setup, and AgentCore Runtime creation.

### Step 3 — Bootstrap CDK

```powershell
cdk bootstrap aws://<account-id>/<region>
```

This creates the CDK staging bucket, ECR assets repository, and deployment roles needed for image assets.

### Step 4 — Create the Python environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Agent container dependencies are installed by Docker during `cdk deploy`.

### Step 5 — Verify source locally

```powershell
ruff check .
mypy .
pytest tests\unit
```

Optional local A2A server tests can start each agent with environment variables and a model stub. A real local model invocation still requires Bedrock credentials.

### Step 6 — Synthesize and inspect

```powershell
cdk synth `
  --context modelId=<model-or-inference-profile-id> `
  --context invokerPrincipalArn=<iam-user-or-role-arn>
```

Inspect synthesized resources for:

- Two `AWS::BedrockAgentCore::Runtime` resources.
- A2A protocol on both.
- IAM authorizer on both.
- ARM64 image assets.
- Separate execution roles.
- Main-only invoke permission on the weather runtime.
- Invoker-only invoke permission on the main runtime.
- No wildcard `bedrock-agentcore:InvokeAgentRuntime` grants.

### Step 7 — Deploy

```powershell
cdk deploy `
  --context modelId=<model-or-inference-profile-id> `
  --context invokerPrincipalArn=<iam-user-or-role-arn> `
  --require-approval broadening
```

CDK will:

1. Build the weather ARM64 image.
2. Build the main ARM64 image.
3. Push assets to the CDK ECR repository.
4. Create execution roles and observability permissions.
5. Create the weather A2A runtime.
6. Create the main A2A runtime with the weather ARN environment variable.
7. Add the main-to-weather invocation grant.
8. Create the demo invoker role and main invocation grant.
9. Output runtime and role ARNs.

### Step 8 — Verify Agent Cards and health

Use:

```powershell
python scripts\get_agent_card.py `
  --runtime-arn <MainRuntimeArn> `
  --role-arn <DemoInvokerRoleArn>
```

Validate the card exposes:

- Main agent identity.
- JSON-RPC transport.
- A2A protocol version generated by the installed SDK.
- Runtime invocation URL.
- Travel concierge skill metadata.

AgentCore performs `/ping` health checks. CloudFormation/runtime status must be ready before smoke tests.

### Step 9 — Run the delegation example

```powershell
python scripts\invoke_main.py `
  --runtime-arn <MainRuntimeArn> `
  --role-arn <DemoInvokerRoleArn> `
  --prompt "I am visiting Tokyo in April. What weather should I expect, and what should I pack?"
```

Expected behavior:

- Main agent selects `consult_weather_packing_specialist`.
- Main runtime makes a SigV4 `InvokeAgentRuntime` call to the weather runtime.
- The A2A request method is `message/send`.
- The weather agent calls `lookup_demo_weather`.
- Final answer includes:
  - Tokyo April demo conditions.
  - Clothing and rain-related packing advice.
  - An explicit statement that values are deterministic demo data.

Illustrative answer:

```text
The weather specialist reports deterministic demo data for Tokyo in April:
roughly 10–19 C with mild, changeable conditions and a moderate chance of
showers. Pack light layers, a compact waterproof jacket or umbrella,
comfortable water-resistant walking shoes, and one warmer evening layer.
```

### Step 10 — Run the no-delegation example

```powershell
python scripts\invoke_main.py `
  --runtime-arn <MainRuntimeArn> `
  --role-arn <DemoInvokerRoleArn> `
  --prompt "Explain the difference between a direct flight and a nonstop flight in two sentences."
```

Expected behavior:

- Main agent does not select the specialist tool.
- Main agent answers from its own travel-concierge capability.
- Weather runtime is not invoked.

Illustrative answer:

```text
A nonstop flight travels from origin to destination without any intermediate
stops. A direct flight keeps the same flight number but may stop en route, and
passengers may remain onboard or continue on the same aircraft.
```

### Step 11 — Prove routing in observability

1. Open CloudWatch GenAI Observability.
2. Locate the main runtime trace using the invocation time/session ID.
3. For the delegation prompt, verify:
   - Main agent tool selection span.
   - `InvokeAgentRuntime` call to the weather runtime.
   - Weather runtime/model/tool spans.
4. For the no-delegation prompt, verify:
   - Main model span.
   - No specialist tool span.
   - No weather runtime invocation for that correlation ID.
5. Review runtime log groups under `/aws/bedrock-agentcore/runtimes/`.

The implementation will emit structured logs such as:

```json
{
  "event": "specialist_invocation",
  "delegated_to_subagent": true,
  "target_runtime_id": "WeatherPackingSpecialist-...",
  "session_id": "...",
  "outcome": "success"
}
```

No-delegation requests will not emit `specialist_invocation`; main request logs can include `delegated_to_subagent: false` if the framework exposes a reliable post-run tool-usage hook.

### Step 12 — Clean up

```powershell
cdk destroy `
  --context modelId=<model-or-inference-profile-id> `
  --context invokerPrincipalArn=<iam-user-or-role-arn>
```

Then verify:

- Both AgentCore runtimes are deleted.
- The demo invoker role and execution roles are deleted.
- Runtime-specific log groups follow the chosen removal/retention policy.
- CDK bootstrap resources remain shared and are not deleted unless the account owner deliberately removes the bootstrap stack.

## 8. IAM Detail

### Deployment identity

For a demo, an administrator may deploy. For controlled environments, create a deployment role that can:

- Manage this CloudFormation stack.
- Publish CDK assets to its bootstrap S3/ECR resources.
- Create/pass the specifically named AgentCore execution and demo invoker roles.
- Create/update/delete AgentCore runtimes.
- Configure required CloudWatch/X-Ray delivery policies.

Do not attach `AdministratorAccess` to runtime roles.

### Weather runtime execution role

Allowed:

- Invoke the configured Bedrock model/profile.
- Write its logs, metrics, and traces.
- Pull its image.

Not allowed:

- Invoke the main runtime.
- Invoke arbitrary AgentCore runtimes.
- Assume the demo caller role.

### Main runtime execution role

Allowed:

- Everything required for its own model/observability/image.
- `bedrock-agentcore:InvokeAgentRuntime` only on the weather runtime ARN.

Not allowed:

- Invoke arbitrary runtimes.
- `InvokeAgentRuntimeForUser` because this demo does not forward an end-user ID.

### Demo invoker role

Trust:

- Only the user/role ARN supplied through CDK context.

Allowed:

- `bedrock-agentcore:InvokeAgentRuntime` only on the main runtime.

Not allowed:

- Invoke the weather runtime directly.
- Pass/modify execution roles.
- Invoke on behalf of arbitrary user IDs.

## 9. Model Permission Strategy

The model ID is portable, but IAM resource scoping differs between:

- Foundation model IDs.
- System inference profiles.
- Application inference profiles.
- Cross-region inference profiles.

Implementation will:

1. Identify the selected identifier type during deployment configuration.
2. Add only the necessary profile ARN and underlying foundation-model ARN patterns.
3. Cover destination regions required by a cross-region inference profile.
4. Avoid `Resource: "*"` for Bedrock invocation unless AWS requires it for a documented operation.
5. Document the generated resources in `cdk synth` output and README.

For production, replace the portable demo policy helper with a model allowlist specific to the organization.

## 10. Error Handling and Reliability

- Missing environment variables stop the container at startup with explicit errors.
- Invalid A2A input returns protocol-appropriate errors through the SDK.
- Subagent access denied is surfaced; the main agent must not fabricate weather.
- Malformed/empty subagent results are errors.
- Retry only documented transient conditions, with at most three attempts.
- Boto3 standard retry mode handles retryable AWS transport/service failures.
- A2A `-32054` retryable session conflicts receive explicit short exponential backoff.
- Logs avoid full prompts and credentials.
- Session IDs and request IDs allow correlation.
- Deterministic fixtures make demonstrations and assertions stable.

## 11. Security and Production-Hardening Notes

The demo is least-privilege by default but is not a complete production platform. Before production:

- Use a VPC design and approved egress controls if required by policy.
- Add permissions boundaries and organization SCP alignment.
- Use application inference profiles for cost attribution and quotas.
- Add runtime resource-based policies for cross-account scenarios.
- Add input/output content controls appropriate to the business domain.
- Add prompt-injection defenses around any future external tools.
- Encrypt and retain logs according to policy.
- Define CloudWatch alarms for errors, throttles, latency, and model spend.
- Define runtime qualifiers/versions and a controlled promotion strategy.
- Pin image digests and dependencies; add image and dependency scanning.
- Add concurrency/load tests and quota reviews.
- Replace deterministic weather fixtures with an approved provider only after adding secrets management, egress controls, attribution, timeouts, and provider-specific failure handling.

## 12. Validation and Acceptance Criteria

The implementation is accepted when:

1. `ruff`, `mypy`, and all unit tests pass.
2. `cdk synth` produces two A2A AgentCore Runtime resources.
3. Both images build for ARM64.
4. Both runtimes reach ready status.
5. The main Agent Card is retrievable using IAM/SigV4.
6. A weather/packing prompt causes exactly one main-to-subagent A2A invocation.
7. The specialist answer is incorporated and labeled as deterministic demo data.
8. A general travel prompt returns a correct main-agent answer with no subagent invocation.
9. An unauthorized principal cannot invoke either runtime.
10. The demo invoker role cannot invoke the subagent directly.
11. CloudWatch/X-Ray provides evidence for both routing branches.
12. `cdk destroy` removes demo-specific compute and IAM resources.

## 13. Implementation Todos

1. **Scaffold the Python and CDK project**
   - Add root configuration, dependency files, typed deployment configuration, and documentation shell.
2. **Implement shared A2A request and response utilities**
   - Add typed JSON-RPC request construction, strict response extraction, and retryable error classification.
3. **Implement the weather and packing subagent**
   - Add deterministic fixtures, validated lookup tool, specialist prompt, A2A entrypoint, requirements, and ARM64 Dockerfile.
4. **Implement the main travel concierge**
   - Add specialist client, model-selected tool, routing prompt, A2A entrypoint, requirements, and ARM64 Dockerfile.
5. **Implement CDK infrastructure**
   - Add roles, model permissions, ARM64 assets, two IAM-authorized A2A runtimes, invocation grants, observability, and outputs.
6. **Implement operator scripts**
   - Add role assumption, SigV4 invocation, Agent Card retrieval, and two-branch smoke tests.
7. **Add unit and deployed integration tests**
   - Cover protocol parsing, retry behavior, fixtures, routing, permissions, and deployed behavior.
8. **Document deployment and operations**
   - Complete setup, deployment, verification, troubleshooting, observability, cost, hardening, and cleanup instructions.
9. **Validate end to end**
   - Run static checks and tests, synthesize, inspect IAM, deploy, test both routing branches, verify telemetry, and destroy a test deployment.

## 14. Key Source References

- AWS: Deploy A2A servers in AgentCore Runtime  
  https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a.html
- AWS: A2A protocol contract  
  https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a-protocol-contract.html
- AWS: IAM permissions for AgentCore Runtime  
  https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html
- AWS: AgentCore observability  
  https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability.html
- AWS CDK: `aws_bedrockagentcore.Runtime`  
  https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_bedrockagentcore.Runtime.html
- AWS CDK: `AgentRuntimeArtifact`  
  https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_bedrockagentcore.AgentRuntimeArtifact.html
- AWS CDK: `IBedrockAgentRuntime.grantInvokeRuntime`  
  https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_bedrockagentcore.IBedrockAgentRuntime.html
- Boto3: `invoke_agent_runtime`  
  https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-agentcore/client/invoke_agent_runtime.html
- A2A protocol  
  https://a2a-protocol.org/

## 15. Version-Sensitivity Note

Amazon Bedrock AgentCore and its CDK/SDK integrations are evolving quickly. Before implementation, confirm:

- Current package versions and Python compatibility.
- The boto3 response member name and streaming-body behavior.
- The installed CDK Python method names for `from_asset`, `using_public_network`, and `grant_invoke_runtime`.
- The A2A protocol version emitted by `serve_a2a`.
- Model/inference-profile IAM resource requirements for the chosen region and identifier.

These checks are implementation safeguards, not unresolved architectural decisions.
