import enum
from typing import Protocol, runtime_checkable

import shapely


__all__ = [
    "ProviderToken",
    "BorderProvider",
]


class ProviderToken(enum.Enum):
    BORDER_PROVIDER = 0


@runtime_checkable
class BorderProvider(Protocol):
    def get_border(border_name: str) -> shapely.LineString: ...
