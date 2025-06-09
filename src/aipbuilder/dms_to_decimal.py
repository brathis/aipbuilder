import re
from typing import Tuple


__all__ = [
    "is_valid_dms_format",
    "dms_string_to_decimal",
    "dms_to_decimal",
    "dms_match_to_decimal",
]


_REGEX = re.compile(
    r"^(?P<degLat>\d{2}) (?P<minLat>\d{2}) (?P<secLat>[\d\.]{2,5}) (?P<hemLat>N|S) (/ )?(?P<degLon>\d{3}) (?P<minLon>\d{2}) (?P<secLon>[\d\.]{2,5}) (?P<hemLon>E|W)$"
)


def is_valid_dms_format(dms: str) -> re.Match | None:
    return _REGEX.fullmatch(dms)


def dms_string_to_decimal(dms: str) -> Tuple[float, float]:
    match = _REGEX.fullmatch(dms)
    if not match:
        raise ValueError(f'invalid value "{dms}"')
    return dms_match_to_decimal(match)


def dms_match_to_decimal(match: re.Match) -> Tuple[float, float]:
    x = dms_to_decimal(
        int(match["degLon"]), int(match["minLon"]), float(match["secLon"])
    ) * (1 if match["hemLon"] == "E" else -1)
    y = dms_to_decimal(
        int(match["degLat"]), int(match["minLat"]), float(match["secLat"])
    ) * (1 if match["hemLat"] == "N" else -1)
    return (x, y)


def dms_to_decimal(d: float, m: float, s: float) -> float:
    return d + m / 60 + s / 3600
