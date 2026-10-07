from __future__ import annotations

from strands import tool

from agents.weather_agent.weather_fixtures import find_fixture


@tool
def lookup_demo_weather(destination: str, month: int) -> str:
    """Return deterministic demo weather for a destination and travel month."""
    fixture = find_fixture(destination, month)
    source = "DEMO CLIMATOLOGY FALLBACK" if fixture.fallback else "DEMO WEATHER DATA"
    return (
        f"{source} for {fixture.destination}, month {fixture.month}: "
        f"{fixture.summary}; {fixture.low_c}-{fixture.high_c} C; "
        f"rain likelihood: {fixture.rain_likelihood}; "
        f"conditions: {', '.join(fixture.conditions)}. "
        "These values are deterministic demo data, not a live forecast."
    )

