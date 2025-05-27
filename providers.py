import enum
from typing import Protocol

import shapely


__all__ = [
    "ProviderToken",
    "BorderProvider",
]


class ProviderToken(enum.Enum):
    BORDER_PROVIDER = 0


class BorderProvider(Protocol):
    def get_border(border_name: str) -> shapely.MultiLineString: ...
