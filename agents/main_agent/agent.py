from __future__ import annotations

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
When you use it, preserve its statement that weather values are deterministic demo data.
If the specialist call fails, clearly say specialist advice is unavailable; do not invent weather.
""".strip()


def build_specialist_tool(
    ask_specialist: Callable[[str], str],
) -> Callable[[str, int, str], str]:
    @tool
    def consult_weather_packing_specialist(
        destination: str,
        travel_month: int,
        traveler_context: str = "",
    ) -> str:
        """Use only for destination weather or weather-aware packing advice."""
        request = (
            f"Destination: {destination.strip()}\n"
            f"Travel month: {travel_month}\n"
            f"Traveler context: {traveler_context.strip() or 'not provided'}\n"
            "Provide conditions and weather-aware packing advice."
        )
        return ask_specialist(request)

    return consult_weather_packing_specialist


def create_main_agent(model_id: str, ask_specialist: Callable[[str], str]) -> Agent:
    return Agent(
        model=model_id,
        system_prompt=MAIN_AGENT_PROMPT,
        tools=[build_specialist_tool(ask_specialist)],
    )

