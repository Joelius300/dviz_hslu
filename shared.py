from datetime import datetime
from typing import Optional, NamedTuple

import pytz

PROJECT_TIMEZONE = pytz.timezone("Europe/Zurich")


class ThresholdCrossings(NamedTuple):
    upper: Optional[datetime]
    lower: Optional[datetime]


HitTimes = dict[str, ThresholdCrossings]


class Thresholds(NamedTuple):
    upper: float | int
    lower: float | int


def is_in_winter_mode(timestamp: datetime):
    # it's not symmetrical, and varies per year; usually the heating unit stays in winter mode longer
    return timestamp.month < 5 or timestamp.month >= 10


def rgb(r: int, g: int, b: int):
    return f'rgb({r},{g},{b})'


def rgba(r: int, g: int, b: int, a=1.0):
    return f'rgba({r},{g},{b},{a})'
