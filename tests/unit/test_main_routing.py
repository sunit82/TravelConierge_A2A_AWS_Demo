from agents.main_agent.agent import MAIN_AGENT_PROMPT, build_specialist_tool


def test_specialist_tool_forwards_structured_request_once() -> None:
    requests: list[str] = []

    def fake_specialist(request: str) -> str:
        requests.append(request)
        return "Deterministic demo data and packing advice"

    tool = build_specialist_tool(fake_specialist)
    result = tool("Tokyo", 4, "travelling with children")

    assert result == "Deterministic demo data and packing advice"
    assert len(requests) == 1
    assert "Destination: Tokyo" in requests[0]
    assert "Travel month: 4" in requests[0]


def test_prompt_defines_positive_and_negative_routing_rules() -> None:
    assert "Call consult_weather_packing_specialist" in MAIN_AGENT_PROMPT
    assert "Do not call the specialist for general questions" in MAIN_AGENT_PROMPT
    assert "flight terminology" in MAIN_AGENT_PROMPT
    assert "do not invent weather" in MAIN_AGENT_PROMPT

