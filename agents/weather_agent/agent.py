from __future__ import annotations

from strands import Agent

from agents.weather_agent.weather_tool import lookup_demo_weather

WEATHER_AGENT_PROMPT = """
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
""".strip()


def create_weather_agent(model_id: str) -> Agent:
    return Agent(
        model=model_id,
        system_prompt=WEATHER_AGENT_PROMPT,
        tools=[lookup_demo_weather],
    )

