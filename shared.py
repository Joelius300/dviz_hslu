from datetime import datetime
from typing import Optional

HitTimes = dict[str, list[Optional[datetime], Optional[datetime]]]


def is_in_winter_mode(timestamp: datetime):
    # it's not symmetrical, and varies per year; usually the heating unit stays in winter mode longer
    return timestamp.month < 5 or timestamp.month >= 10
