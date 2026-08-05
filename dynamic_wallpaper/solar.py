"""Solar event calculations used to align dynamic wallpaper schedules."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime


class SolarError(RuntimeError):
    """Raised when solar events cannot be resolved for a location or date."""


@dataclass(frozen=True)
class SolarEvents:
    """Civil-twilight and solar-noon times expressed as local minutes."""

    civil_dawn: int
    solar_noon: int
    civil_dusk: int


def calculate_solar_events(
    day: date,
    latitude: float,
    longitude: float,
    *,
    timezone_offset_minutes: int,
) -> SolarEvents:
    """Calculate local civil dawn, solar noon, and civil dusk.

    The implementation follows NOAA's published solar-position equations and
    intentionally uses civil twilight (solar zenith 96 degrees) as the visual
    boundary between night and daylight wallpaper phases.
    """
    if not -90 <= latitude <= 90:
        raise SolarError(f"Latitude is outside the valid range: {latitude}")
    if not -180 <= longitude <= 180:
        raise SolarError(f"Longitude is outside the valid range: {longitude}")

    julian_day = _julian_day(day)
    century = (julian_day - 2451545.0) / 36525.0
    mean_longitude = (
        280.46646 + century * (36000.76983 + century * 0.0003032)
    ) % 360
    mean_anomaly = 357.52911 + century * (35999.05029 - 0.0001537 * century)
    eccentricity = 0.016708634 - century * (
        0.000042037 + 0.0000001267 * century
    )

    anomaly_radians = math.radians(mean_anomaly)
    equation_of_center = (
        math.sin(anomaly_radians)
        * (1.914602 - century * (0.004817 + 0.000014 * century))
        + math.sin(2 * anomaly_radians) * (0.019993 - 0.000101 * century)
        + math.sin(3 * anomaly_radians) * 0.000289
    )
    true_longitude = mean_longitude + equation_of_center
    omega = 125.04 - 1934.136 * century
    apparent_longitude = (
        true_longitude - 0.00569 - 0.00478 * math.sin(math.radians(omega))
    )

    mean_obliquity = (
        23
        + (
            26
            + (
                21.448
                - century * (46.815 + century * (0.00059 - century * 0.001813))
            )
            / 60
        )
        / 60
    )
    corrected_obliquity = mean_obliquity + 0.00256 * math.cos(
        math.radians(omega)
    )
    declination = math.degrees(
        math.asin(
            math.sin(math.radians(corrected_obliquity))
            * math.sin(math.radians(apparent_longitude))
        )
    )

    y = math.tan(math.radians(corrected_obliquity / 2)) ** 2
    equation_of_time = 4 * math.degrees(
        y * math.sin(2 * math.radians(mean_longitude))
        - 2 * eccentricity * math.sin(anomaly_radians)
        + 4
        * eccentricity
        * y
        * math.sin(anomaly_radians)
        * math.cos(2 * math.radians(mean_longitude))
        - 0.5 * y * y * math.sin(4 * math.radians(mean_longitude))
        - 1.25 * eccentricity * eccentricity * math.sin(2 * anomaly_radians)
    )

    noon_utc = 720 - 4 * longitude - equation_of_time
    hour_angle = _hour_angle(latitude, declination, zenith=96.0)
    dawn_utc = noon_utc - 4 * hour_angle
    dusk_utc = noon_utc + 4 * hour_angle

    dawn = round(dawn_utc + timezone_offset_minutes)
    noon = round(noon_utc + timezone_offset_minutes)
    dusk = round(dusk_utc + timezone_offset_minutes)

    if not 0 <= dawn < noon < dusk < 1440:
        raise SolarError(
            "Solar events do not form a usable local-day schedule for "
            f"{day.isoformat()} at {latitude}, {longitude}"
        )

    return SolarEvents(dawn, noon, dusk)


def timezone_offset_for(value: datetime) -> int:
    """Return the local UTC offset for the date represented by ``value``."""
    if value.tzinfo is None:
        aware = value.astimezone()
    else:
        aware = value
    offset = aware.utcoffset()
    if offset is None:
        raise SolarError("Could not determine the local timezone offset")
    return round(offset.total_seconds() / 60)


def _julian_day(day: date) -> float:
    year = day.year
    month = day.month
    decimal_day = day.day
    if month <= 2:
        year -= 1
        month += 12
    a = year // 100
    b = 2 - a + a // 4
    return (
        math.floor(365.25 * (year + 4716))
        + math.floor(30.6001 * (month + 1))
        + decimal_day
        + b
        - 1524.5
    )


def _hour_angle(
    latitude: float, declination: float, *, zenith: float
) -> float:
    latitude_radians = math.radians(latitude)
    declination_radians = math.radians(declination)
    denominator = math.cos(latitude_radians) * math.cos(declination_radians)
    if math.isclose(denominator, 0.0, abs_tol=1e-12):
        raise SolarError("Solar events are unavailable at this latitude")
    cosine = math.cos(math.radians(zenith)) / denominator - math.tan(
        latitude_radians
    ) * math.tan(declination_radians)
    if cosine < -1 or cosine > 1:
        raise SolarError(
            "Civil dawn and dusk are unavailable for this date and location"
        )
    return math.degrees(math.acos(cosine))
