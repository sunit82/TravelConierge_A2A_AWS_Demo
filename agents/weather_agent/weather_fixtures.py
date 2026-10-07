from __future__ import annotations

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
    fallback: bool = False


WEATHER_FIXTURES: dict[tuple[str, int], WeatherFixture] = {
    ("tokyo", 4): WeatherFixture(
        destination="Tokyo",
        month=4,
        summary="Mild spring weather with changeable rain",
        low_c=10,
        high_c=19,
        rain_likelihood="moderate",
        conditions=("mild afternoons", "cool evenings", "showers"),
    ),
    ("reykjavik", 12): WeatherFixture(
        destination="Reykjavik",
        month=12,
        summary="Cold, windy winter conditions with short daylight hours",
        low_c=-2,
        high_c=4,
        rain_likelihood="moderate, with possible sleet or snow",
        conditions=("cold", "windy", "mixed precipitation"),
    ),
    ("singapore", 7): WeatherFixture(
        destination="Singapore",
        month=7,
        summary="Hot and humid tropical conditions with frequent showers",
        low_c=25,
        high_c=32,
        rain_likelihood="high",
        conditions=("hot", "humid", "heavy showers"),
    ),
}


def find_fixture(destination: str, month: int) -> WeatherFixture:
    normalized = destination.strip()
    if not normalized:
        raise ValueError("Destination must not be blank")
    if len(normalized) > 100:
        raise ValueError("Destination must be 100 characters or fewer")
    if not 1 <= month <= 12:
        raise ValueError("Month must be between 1 and 12")

    known = WEATHER_FIXTURES.get((normalized.casefold(), month))
    if known is not None:
        return known

    return WeatherFixture(
        destination=normalized,
        month=month,
        summary="Generic demo climatology; no destination-specific fixture is available",
        low_c=10,
        high_c=24,
        rain_likelihood="variable",
        conditions=("variable temperatures", "possible rain"),
        fallback=True,
    )

