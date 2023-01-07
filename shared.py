from datetime import datetime
from typing import Optional, NamedTuple


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
