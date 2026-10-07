from __future__ import annotations

import os

import pytest

from scripts.get_agent_card import get_agent_card
from scripts.invoke_main import invoke
from scripts.smoke_test import DELEGATION_PROMPT, DIRECT_PROMPT

MAIN_RUNTIME_ARN = os.getenv("MAIN_RUNTIME_ARN")
DEMO_INVOKER_ROLE_ARN = os.getenv("DEMO_INVOKER_ROLE_ARN")
pytestmark = pytest.mark.integration


def require_deployment() -> tuple[str, str]:
    if not MAIN_RUNTIME_ARN or not DEMO_INVOKER_ROLE_ARN:
        pytest.skip("Set MAIN_RUNTIME_ARN and DEMO_INVOKER_ROLE_ARN")
    return MAIN_RUNTIME_ARN, DEMO_INVOKER_ROLE_ARN


def test_main_agent_card_is_retrievable() -> None:
    runtime_arn, role_arn = require_deployment()
    card = get_agent_card(runtime_arn, role_arn)

    assert card


def test_delegation_response_contains_demo_disclosure() -> None:
    runtime_arn, role_arn = require_deployment()
    answer, _ = invoke(runtime_arn, role_arn, DELEGATION_PROMPT)

    assert "demo" in answer.casefold()
    assert "pack" in answer.casefold()


def test_general_question_returns_direct_answer() -> None:
    runtime_arn, role_arn = require_deployment()
    answer, _ = invoke(runtime_arn, role_arn, DIRECT_PROMPT)

    assert "direct" in answer.casefold()
    assert "nonstop" in answer.casefold()

