from datetime import datetime
from typing import Optional, NamedTuple

import pytz

PROJECT_TIMEZONE = pytz.timezone("Europe/Zurich")


class ThresholdCrossings(NamedTuple):
    """A tuple holding the first times a temperature crossed the upper and lower threshold respectively."""
    upper: Optional[datetime]
    lower: Optional[datetime]


HitTimes = dict[str, ThresholdCrossings]
"""A dictionary which holds the points in time multiple temperatures crossed the thresholds."""


class Thresholds(NamedTuple):
    """A tuple holding the temperature thresholds in °C."""
    upper: float | int
    lower: float | int


def is_in_winter_mode(timestamp: datetime) -> bool:
    """Returns an estimation whether the heating unit was in winter mode at that time."""
    # it's not symmetrical, and varies per year; usually the heating unit stays in winter mode longer
    return timestamp.month < 5 or timestamp.month >= 10


def rgb(r: int, g: int, b: int):
    return f'rgb({r},{g},{b})'


def rgba(r: int, g: int, b: int, a=1.0):
    return f'rgba({r},{g},{b},{a})'
