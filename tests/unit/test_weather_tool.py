import pytest

from agents.weather_agent.weather_fixtures import find_fixture
from agents.weather_agent.weather_tool import lookup_demo_weather


def test_known_fixture_is_normalized() -> None:
    fixture = find_fixture("  TOKYO ", 4)

    assert fixture.destination == "Tokyo"
    assert fixture.low_c == 10
    assert fixture.high_c == 19
    assert fixture.fallback is False


def test_tool_labels_known_data_as_demo() -> None:
    result = lookup_demo_weather("Tokyo", 4)

    assert "DEMO WEATHER DATA" in result
    assert "10-19 C" in result
    assert "not a live forecast" in result


def test_unknown_destination_uses_labeled_fallback() -> None:
    result = lookup_demo_weather("Lisbon", 5)

    assert "DEMO CLIMATOLOGY FALLBACK" in result
    assert "no destination-specific fixture" in result
    assert "not a live forecast" in result


@pytest.mark.parametrize(
    ("destination", "month"),
    [("", 4), ("Tokyo", 0), ("Tokyo", 13), ("x" * 101, 4)],
)
def test_invalid_lookup_is_rejected(destination: str, month: int) -> None:
    with pytest.raises(ValueError):
        find_fixture(destination, month)

