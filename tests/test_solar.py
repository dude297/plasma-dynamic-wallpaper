"""Tests for solar-event calculations."""

from datetime import UTC, date, datetime

import pytest

from dynamic_wallpaper.solar import (
    SolarError,
    calculate_solar_events,
    timezone_offset_for,
)


def test_calculate_solar_events_for_san_jose_summer() -> None:
    events = calculate_solar_events(
        date(2026, 8, 4),
        37.3382,
        -121.8863,
        timezone_offset_minutes=-420,
    )

    assert 330 <= events.civil_dawn <= 370
    assert 770 <= events.solar_noon <= 800
    assert 1210 <= events.civil_dusk <= 1250


def test_calculate_solar_events_rejects_polar_twilight_gap() -> None:
    with pytest.raises(SolarError, match="unavailable"):
        calculate_solar_events(
            date(2026, 6, 21),
            89.0,
            0.0,
            timezone_offset_minutes=0,
        )


def test_timezone_offset_for_aware_datetime() -> None:
    value = datetime(2026, 8, 4, 12, tzinfo=UTC)

    assert timezone_offset_for(value) == 0
